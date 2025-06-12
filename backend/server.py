from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import json
import discord
from discord.ext import commands

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Discord bot setup
DISCORD_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
APPLICATION_ID = os.environ.get('DISCORD_APPLICATION_ID')

# Discord bot instance
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.members = True  # للحصول على أحداث الأعضاء
bot = commands.Bot(command_prefix='!', intents=intents)

# Global variables for bot status and active guild settings
bot_status = {
    'running': False,
    'connected': False,
    'last_error': None
}

# Store active guild configurations for welcome messages etc.
active_guild_configs = {}

# Create the main app
app = FastAPI(title="Discord Server Manager", version="1.0.0")

# Create API router
api_router = APIRouter(prefix="/api")

# Pydantic Models
class ServerConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    icon_url: Optional[str] = None
    roles: List[Dict[str, Any]]
    channels: List[Dict[str, Any]]
    welcome_settings: Optional[Dict[str, Any]] = None
    auto_role_settings: Optional[Dict[str, Any]] = None
    moderation_settings: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ServerConfigCreate(BaseModel):
    name: str
    description: str
    icon_url: Optional[str] = None
    roles: List[Dict[str, Any]]
    channels: List[Dict[str, Any]]
    welcome_settings: Optional[Dict[str, Any]] = None
    auto_role_settings: Optional[Dict[str, Any]] = None
    moderation_settings: Optional[Dict[str, Any]] = None

class SetupRequest(BaseModel):
    guild_id: str
    config_id: str

class SetupStatus(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    guild_id: str
    config_id: str
    status: str  # pending, running, completed, failed
    progress: int = 0
    message: str = ""
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

# Discord Bot Events
@bot.event
async def on_ready():
    global bot_status
    print(f'{bot.user} قد اتصل بنجاح!')
    bot_status['connected'] = True
    bot_status['running'] = True
    bot_status['last_error'] = None
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"تم مزامنة {len(synced)} أمر.")
    except Exception as e:
        print(f"فشل في مزامنة الأوامر: {e}")

@bot.event
async def on_member_join(member):
    """Handle new member joining the server"""
    try:
        guild_id = str(member.guild.id)
        
        # Get guild configuration from database
        config = await db.server_configs.find_one({"guild_id": guild_id})
        if not config:
            return
        
        welcome_settings = config.get('welcome_settings', {})
        if not welcome_settings.get('enabled', False):
            return
        
        # Send welcome message
        welcome_channel_name = welcome_settings.get('channel', 'الترحيب')
        welcome_channel = discord.utils.get(member.guild.channels, name=welcome_channel_name)
        
        if welcome_channel:
            # Create welcome message
            welcome_message = welcome_settings.get('message', 'مرحباً {user} في {server}! 🎉')
            welcome_message = welcome_message.format(
                user=member.mention,
                server=member.guild.name,
                username=member.display_name
            )
            
            # Create embed if specified
            if welcome_settings.get('use_embed', True):
                embed = discord.Embed(
                    title=welcome_settings.get('title', 'مرحباً بك! 🎉'),
                    description=welcome_message,
                    color=discord.Color(int(welcome_settings.get('color', '#00ff00').replace('#', ''), 16))
                )
                
                if welcome_settings.get('thumbnail'):
                    embed.set_thumbnail(url=member.display_avatar.url)
                
                if welcome_settings.get('footer'):
                    embed.set_footer(text=welcome_settings['footer'])
                    
                await welcome_channel.send(embed=embed)
            else:
                await welcome_channel.send(welcome_message)
        
        # Auto-assign roles
        auto_role_settings = config.get('auto_role_settings', {})
        if auto_role_settings.get('enabled', False):
            role_names = auto_role_settings.get('roles', [])
            for role_name in role_names:
                role = discord.utils.get(member.guild.roles, name=role_name)
                if role:
                    await member.add_roles(role)
                    
    except Exception as e:
        print(f"Error handling member join: {e}")

@bot.event
async def on_member_remove(member):
    """Handle member leaving the server"""
    try:
        guild_id = str(member.guild.id)
        
        # Get guild configuration from database
        config = await db.server_configs.find_one({"guild_id": guild_id})
        if not config:
            return
            
        welcome_settings = config.get('welcome_settings', {})
        if not welcome_settings.get('goodbye_enabled', False):
            return
        
        # Send goodbye message
        goodbye_channel_name = welcome_settings.get('goodbye_channel', 'الترحيب')
        goodbye_channel = discord.utils.get(member.guild.channels, name=goodbye_channel_name)
        
        if goodbye_channel:
            goodbye_message = welcome_settings.get('goodbye_message', 'وداعاً {username}! 👋')
            goodbye_message = goodbye_message.format(
                username=member.display_name,
                server=member.guild.name
            )
            
            if welcome_settings.get('use_embed', True):
                embed = discord.Embed(
                    title='وداعاً! 👋',
                    description=goodbye_message,
                    color=discord.Color.red()
                )
                await goodbye_channel.send(embed=embed)
            else:
                await goodbye_channel.send(goodbye_message)
                
    except Exception as e:
        print(f"Error handling member remove: {e}")

# Discord slash commands
@bot.tree.command(name="setup_server", description="إعداد السيرفر باستخدام ملف JSON")
async def setup_server_command(interaction: discord.Interaction, config_name: str):
    """Command to setup server using saved configuration"""
    await interaction.response.defer()
    
    try:
        # Find configuration by name
        config_doc = await db.server_configs.find_one({"name": config_name})
        if not config_doc:
            await interaction.followup.send(f"❌ لم يتم العثور على إعداد بالاسم: {config_name}")
            return
        
        # Store guild ID in config for future use
        await db.server_configs.update_one(
            {"name": config_name},
            {"$set": {"guild_id": str(interaction.guild.id)}}
        )
        
        # Create setup status
        setup_status = SetupStatus(
            guild_id=str(interaction.guild.id),
            config_id=config_doc['id'],
            status="running",
            message="بدء إعداد السيرفر..."
        )
        
        await db.setup_status.insert_one(setup_status.dict())
        
        await interaction.followup.send(f"🚀 بدء إعداد السيرفر باستخدام: {config_name}")
        
        # Run server setup in background
        success = await setup_discord_server(interaction.guild, config_doc, setup_status.id)
        
        if success:
            # Send detailed setup completion message
            embed = discord.Embed(
                title="✅ تم إعداد السيرفر بنجاح!",
                description=f"تم إنشاء السيرفر باستخدام إعداد: **{config_name}**",
                color=discord.Color.green()
            )
            
            # Add feature information
            features = []
            if config_doc.get('welcome_settings', {}).get('enabled'):
                features.append("🎉 رسائل الترحيب مفعلة")
            if config_doc.get('auto_role_settings', {}).get('enabled'):
                features.append("👤 توزيع الأدوار التلقائي مفعل")
            
            if features:
                embed.add_field(name="الميزات المفعلة:", value="\n".join(features), inline=False)
                
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ حدث خطأ أثناء إعداد السيرفر.")
            
    except Exception as e:
        await interaction.followup.send(f"❌ خطأ: {str(e)}")

@bot.tree.command(name="configure_welcome", description="إعداد رسائل الترحيب للسيرفر")
async def configure_welcome(interaction: discord.Interaction, 
                          channel_name: str = "الترحيب",
                          message: str = "مرحباً {user} في {server}! 🎉"):
    """Configure welcome messages for the server"""
    try:
        guild_id = str(interaction.guild.id)
        
        # Update welcome settings in database
        welcome_settings = {
            "enabled": True,
            "channel": channel_name,
            "message": message,
            "use_embed": True,
            "title": "مرحباً بك! 🎉",
            "color": "#00ff00",
            "thumbnail": True,
            "footer": f"مرحباً بك في {interaction.guild.name}"
        }
        
        await db.server_configs.update_one(
            {"guild_id": guild_id},
            {"$set": {"welcome_settings": welcome_settings}},
            upsert=True
        )
        
        embed = discord.Embed(
            title="✅ تم إعداد رسائل الترحيب!",
            description=f"القناة: #{channel_name}\nالرسالة: {message}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ خطأ: {str(e)}")

@bot.tree.command(name="configure_autorole", description="إعداد توزيع الأدوار التلقائي")
async def configure_autorole(interaction: discord.Interaction, roles: str):
    """Configure automatic role assignment"""
    try:
        guild_id = str(interaction.guild.id)
        role_list = [role.strip() for role in roles.split(',')]
        
        # Validate roles exist
        valid_roles = []
        for role_name in role_list:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                valid_roles.append(role_name)
        
        if not valid_roles:
            await interaction.response.send_message("❌ لم يتم العثور على أي من الأدوار المحددة.")
            return
        
        auto_role_settings = {
            "enabled": True,
            "roles": valid_roles
        }
        
        await db.server_configs.update_one(
            {"guild_id": guild_id},
            {"$set": {"auto_role_settings": auto_role_settings}},
            upsert=True
        )
        
        embed = discord.Embed(
            title="✅ تم إعداد توزيع الأدوار التلقائي!",
            description=f"الأدوار: {', '.join(valid_roles)}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ خطأ: {str(e)}")

@bot.tree.command(name="test_welcome", description="اختبار رسالة الترحيب")
async def test_welcome(interaction: discord.Interaction):
    """Test welcome message"""
    try:
        # Simulate member join for testing
        member = interaction.user
        
        guild_id = str(interaction.guild.id)
        config = await db.server_configs.find_one({"guild_id": guild_id})
        
        if not config or not config.get('welcome_settings', {}).get('enabled'):
            await interaction.response.send_message("❌ رسائل الترحيب غير مفعلة في هذا السيرفر.")
            return
        
        welcome_settings = config['welcome_settings']
        welcome_message = welcome_settings.get('message', 'مرحباً {user} في {server}! 🎉')
        welcome_message = welcome_message.format(
            user=member.mention,
            server=interaction.guild.name,
            username=member.display_name
        )
        
        embed = discord.Embed(
            title=welcome_settings.get('title', 'مرحباً بك! 🎉'),
            description=welcome_message + "\n\n**(هذه رسالة اختبار)**",
            color=discord.Color(int(welcome_settings.get('color', '#00ff00').replace('#', ''), 16))
        )
        
        if welcome_settings.get('thumbnail'):
            embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.set_footer(text="اختبار رسالة الترحيب")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ خطأ: {str(e)}")

@bot.tree.command(name="list_configs", description="عرض قائمة الإعدادات المحفوظة")
async def list_configs_command(interaction: discord.Interaction):
    """List all saved configurations"""
    try:
        configs = await db.server_configs.find({}, {"name": 1, "description": 1}).to_list(10)
        
        if not configs:
            await interaction.response.send_message("📝 لا توجد إعدادات محفوظة.")
            return
        
        config_list = "\n".join([f"• **{config['name']}**: {config['description']}" for config in configs])
        embed = discord.Embed(
            title="📋 الإعدادات المحفوظة",
            description=config_list,
            color=0x00ff00
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ خطأ: {str(e)}")

# Core Discord server setup function
async def setup_discord_server(guild: discord.Guild, config: Dict, status_id: str):
    """Setup Discord server based on configuration"""
    try:
        # Update status
        await update_setup_status(status_id, "running", 10, "إنشاء الأدوار...")
        
        # Create roles
        role_mapping = await create_roles(guild, config.get('roles', []))
        
        # Update status
        await update_setup_status(status_id, "running", 50, "إنشاء القنوات والتصنيفات...")
        
        # Create categories and channels
        await create_channels_and_categories(guild, config.get('channels', []), role_mapping)
        
        # Update status
        await update_setup_status(status_id, "completed", 100, "تم إعداد السيرفر بنجاح!")
        
        return True
        
    except Exception as e:
        await update_setup_status(status_id, "failed", 0, f"خطأ: {str(e)}")
        print(f"Server setup error: {e}")
        return False

async def create_roles(guild: discord.Guild, roles_config: List[Dict]):
    """Create roles based on configuration"""
    role_mapping = {}
    
    for role_config in roles_config:
        try:
            # Check if role already exists
            existing_role = discord.utils.get(guild.roles, name=role_config['name'])
            if existing_role:
                role_mapping[role_config['name']] = existing_role
                continue
            
            # Create new role
            permissions = discord.Permissions(permissions=role_config.get('permissions', 0))
            color = discord.Color(int(role_config.get('color', '#000000').replace('#', ''), 16))
            
            role = await guild.create_role(
                name=role_config['name'],
                permissions=permissions,
                color=color,
                hoist=role_config.get('hoist', False),
                mentionable=role_config.get('mentionable', False)
            )
            
            role_mapping[role_config['name']] = role
            print(f"Created role: {role_config['name']}")
            
        except Exception as e:
            print(f"Error creating role {role_config['name']}: {e}")
    
    return role_mapping

async def create_channels_and_categories(guild: discord.Guild, channels_config: List[Dict], role_mapping: Dict):
    """Create channels and categories based on configuration"""
    category_mapping = {}
    
    # Sort channels by position
    channels_config.sort(key=lambda x: x.get('position', 0))
    
    for channel_config in channels_config:
        try:
            if channel_config['type'] == 'category':
                # Create category
                category = await guild.create_category(
                    name=channel_config['name'],
                    position=channel_config.get('position', 0)
                )
                category_mapping[channel_config['name']] = category
                print(f"Created category: {channel_config['name']}")
                
            elif channel_config['type'] == 'text':
                # Create text channel
                category = None
                if 'category' in channel_config:
                    category = category_mapping.get(channel_config['category'])
                
                channel = await guild.create_text_channel(
                    name=channel_config['name'],
                    category=category,
                    position=channel_config.get('position', 0)
                )
                print(f"Created text channel: {channel_config['name']}")
                
            elif channel_config['type'] == 'voice':
                # Create voice channel
                category = None
                if 'category' in channel_config:
                    category = category_mapping.get(channel_config['category'])
                
                channel = await guild.create_voice_channel(
                    name=channel_config['name'],
                    category=category,
                    position=channel_config.get('position', 0)
                )
                print(f"Created voice channel: {channel_config['name']}")
                
        except Exception as e:
            print(f"Error creating channel {channel_config['name']}: {e}")

async def update_setup_status(status_id: str, status: str, progress: int, message: str):
    """Update setup status in database"""
    update_data = {
        "status": status,
        "progress": progress,
        "message": message,
        "updated_at": datetime.utcnow()
    }
    
    if status in ["completed", "failed"]:
        update_data["completed_at"] = datetime.utcnow()
    
    await db.setup_status.update_one(
        {"id": status_id},
        {"$set": update_data}
    )

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Discord Server Manager API", "bot_status": bot_status}

@api_router.post("/configs", response_model=ServerConfig)
async def create_server_config(config: ServerConfigCreate):
    """Create a new server configuration"""
    config_obj = ServerConfig(**config.dict())
    await db.server_configs.insert_one(config_obj.dict())
    return config_obj

@api_router.get("/configs", response_model=List[ServerConfig])
async def get_server_configs():
    """Get all server configurations"""
    configs = await db.server_configs.find().to_list(100)
    return [ServerConfig(**config) for config in configs]

@api_router.get("/configs/{config_id}", response_model=ServerConfig)
async def get_server_config(config_id: str):
    """Get a specific server configuration"""
    config = await db.server_configs.find_one({"id": config_id})
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return ServerConfig(**config)

@api_router.put("/configs/{config_id}", response_model=ServerConfig)
async def update_server_config(config_id: str, config: ServerConfigCreate):
    """Update a server configuration"""
    config_dict = config.dict()
    config_dict["updated_at"] = datetime.utcnow()
    
    result = await db.server_configs.update_one(
        {"id": config_id},
        {"$set": config_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    updated_config = await db.server_configs.find_one({"id": config_id})
    return ServerConfig(**updated_config)

@api_router.delete("/configs/{config_id}")
async def delete_server_config(config_id: str):
    """Delete a server configuration"""
    result = await db.server_configs.delete_one({"id": config_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration deleted successfully"}

@api_router.get("/bot/status")
async def get_bot_status():
    """Get bot connection status"""
    return bot_status

@api_router.post("/bot/start")
async def start_bot(background_tasks: BackgroundTasks):
    """Start the Discord bot"""
    global bot_status
    
    if bot_status['running']:
        return {"message": "Bot is already running"}
    
    try:
        background_tasks.add_task(run_discord_bot)
        return {"message": "Bot is starting..."}
    except Exception as e:
        bot_status['last_error'] = str(e)
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {e}")

@api_router.post("/setup")
async def trigger_server_setup(setup: SetupRequest, background_tasks: BackgroundTasks):
    """Trigger server setup via API"""
    try:
        # Find configuration
        config = await db.server_configs.find_one({"id": setup.config_id})
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        # Create setup status
        setup_status = SetupStatus(
            guild_id=setup.guild_id,
            config_id=setup.config_id,
            status="pending",
            message="Setup queued..."
        )
        
        await db.setup_status.insert_one(setup_status.dict())
        
        return {"message": "Server setup queued", "status_id": setup_status.id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/setup/status/{status_id}")
async def get_setup_status(status_id: str):
    """Get setup status"""
    status = await db.setup_status.find_one({"id": status_id})
    if not status:
        raise HTTPException(status_code=404, detail="Setup status not found")
    return status

# Background task to run Discord bot
async def run_discord_bot():
    """Run Discord bot in background"""
    global bot_status
    try:
        bot_status['running'] = True
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        bot_status['running'] = False
        bot_status['connected'] = False
        bot_status['last_error'] = str(e)
        print(f"Bot error: {e}")

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Start Discord bot on app startup"""
    if DISCORD_TOKEN:
        asyncio.create_task(run_discord_bot())

@app.on_event("shutdown")
async def shutdown_db_client():
    """Close database connection on shutdown"""
    if bot.is_closed() is False:
        await bot.close()
    client.close()
