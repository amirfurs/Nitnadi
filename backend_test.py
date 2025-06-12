import requests
import json
import time
import sys
from datetime import datetime

class DiscordServerManagerTester:
    def __init__(self, base_url="https://ea591308-69d0-415b-9d4d-1c08f135c86e.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.created_config_id = None
        self.created_welcome_config_id = None
        self.test_config = {
            "name": f"Test Server Config {datetime.now().strftime('%H%M%S')}",
            "description": "Test configuration for Discord server",
            "roles": [
                {
                    "name": "Admin",
                    "color": "#ff0000",
                    "permissions": 8,
                    "mentionable": True,
                    "hoist": True
                }
            ],
            "channels": [
                {
                    "name": "General",
                    "type": "category",
                    "position": 0
                },
                {
                    "name": "chat",
                    "type": "text",
                    "category": "General",
                    "position": 1
                }
            ]
        }
        
        # Enhanced test config with welcome and auto-role settings
        self.welcome_test_config = {
            "name": f"سيرفر مع ترحيب متقدم {datetime.now().strftime('%H%M%S')}",
            "description": "سيرفر مع رسائل ترحيب وميزات متقدمة",
            "roles": [
                {
                    "name": "🧠 المشرف العام",
                    "color": "#ff0000",
                    "permissions": 8,
                    "mentionable": True,
                    "hoist": True
                },
                {
                    "name": "👤 العضو",
                    "color": "#aaaaaa",
                    "permissions": 104324161,
                    "mentionable": False,
                    "hoist": False
                }
            ],
            "channels": [
                {
                    "name": "📜 الاستقبال",
                    "type": "category",
                    "position": 0
                },
                {
                    "name": "الترحيب",
                    "type": "text",
                    "category": "📜 الاستقبال",
                    "position": 1
                }
            ],
            "welcome_settings": {
                "enabled": True,
                "channel": "الترحيب",
                "message": "أهلاً وسهلاً {user} في {server}! 🎉",
                "use_embed": True,
                "title": "مرحباً بك! 🎉",
                "color": "#00ff00",
                "thumbnail": True,
                "footer": "نتمنى لك وقتاً ممتعاً معنا",
                "goodbye_enabled": True,
                "goodbye_channel": "الترحيب",
                "goodbye_message": "وداعاً {username}! نتمنى أن نراك قريباً 👋"
            },
            "auto_role_settings": {
                "enabled": True,
                "roles": ["👤 العضو"]
            }
        }

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response.text:
                    try:
                        return success, response.json()
                    except:
                        return success, response.text
                return success, None
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text}")
                return False, None

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, None

    def test_health_check(self):
        """Test API health check endpoint"""
        success, response = self.run_test(
            "API Health Check",
            "GET",
            "",
            200
        )
        if success and response:
            print(f"Bot status: {response.get('bot_status', {})}")
        return success

    def test_bot_status(self):
        """Test bot status endpoint"""
        success, response = self.run_test(
            "Bot Status",
            "GET",
            "bot/status",
            200
        )
        if success and response:
            print(f"Bot connected: {response.get('connected', False)}")
            print(f"Bot running: {response.get('running', False)}")
        return success

    def test_list_configs(self):
        """Test listing configurations"""
        success, response = self.run_test(
            "List Configurations",
            "GET",
            "configs",
            200
        )
        if success and response:
            print(f"Found {len(response)} configurations")
            if len(response) > 0:
                print(f"First config: {response[0]['name']}")
        return success

    def test_create_config(self):
        """Test creating a new configuration"""
        success, response = self.run_test(
            "Create Configuration",
            "POST",
            "configs",
            200,
            data=self.test_config
        )
        if success and response:
            self.created_config_id = response.get('id')
            print(f"Created config with ID: {self.created_config_id}")
        return success

    def test_get_config(self):
        """Test getting a specific configuration"""
        if not self.created_config_id:
            print("❌ Cannot test get_config - No config ID available")
            return False
            
        success, response = self.run_test(
            "Get Configuration",
            "GET",
            f"configs/{self.created_config_id}",
            200
        )
        if success and response:
            print(f"Retrieved config: {response['name']}")
        return success

    def test_update_config(self):
        """Test updating a configuration"""
        if not self.created_config_id:
            print("❌ Cannot test update_config - No config ID available")
            return False
            
        updated_config = self.test_config.copy()
        updated_config["description"] = "Updated test description"
        
        success, response = self.run_test(
            "Update Configuration",
            "PUT",
            f"configs/{self.created_config_id}",
            200,
            data=updated_config
        )
        if success and response:
            print(f"Updated config description: {response['description']}")
            if response['description'] == "Updated test description":
                print("✅ Description updated successfully")
            else:
                print("❌ Description not updated correctly")
                success = False
        return success

    def test_delete_config(self):
        """Test deleting a configuration"""
        if not self.created_config_id:
            print("❌ Cannot test delete_config - No config ID available")
            return False
            
        success, _ = self.run_test(
            "Delete Configuration",
            "DELETE",
            f"configs/{self.created_config_id}",
            200
        )
        if success:
            # Verify deletion by trying to get the config
            verify_success, _ = self.run_test(
                "Verify Deletion",
                "GET",
                f"configs/{self.created_config_id}",
                404
            )
            if verify_success:
                print("✅ Configuration successfully deleted")
            else:
                print("❌ Configuration not deleted properly")
                success = False
        return success

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Discord Server Manager API Tests")
        print("=" * 50)
        
        # Test health check and bot status
        self.test_health_check()
        self.test_bot_status()
        
        # Test CRUD operations
        self.test_list_configs()
        self.test_create_config()
        self.test_get_config()
        self.test_update_config()
        self.test_delete_config()
        
        # Print results
        print("\n" + "=" * 50)
        print(f"📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        print("=" * 50)
        
        return self.tests_passed == self.tests_run

def main():
    tester = DiscordServerManagerTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
