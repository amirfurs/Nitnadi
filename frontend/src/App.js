import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [configs, setConfigs] = useState([]);
  const [botStatus, setBotStatus] = useState({});
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showJsonEditor, setShowJsonEditor] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState(null);
  const [setupStatus, setSetupStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Form states
  const [configForm, setConfigForm] = useState({
    name: '',
    description: '',
    icon_url: '',
    roles: [],
    channels: []
  });
  
  const [jsonInput, setJsonInput] = useState('');

  // Default JSON template with welcome settings
  const defaultJsonTemplate = {
    "name": "قالب جديد مع ترحيب",
    "description": "سيرفر مع رسائل ترحيب وميزات متقدمة",
    "icon_url": "",
    "roles": [
      {
        "name": "🧠 المشرف العام",
        "color": "#ff0000",
        "permissions": 8,
        "mentionable": true,
        "hoist": true
      },
      {
        "name": "👤 العضو",
        "color": "#aaaaaa",
        "permissions": 104324161,
        "mentionable": false,
        "hoist": false
      }
    ],
    "channels": [
      {
        "name": "📜 الاستقبال",
        "type": "category",
        "position": 0
      },
      {
        "name": "👋الترحيب",
        "type": "text",
        "category": "📜 الاستقبال",
        "position": 1
      },
      {
        "name": "📌القوانين",
        "type": "text",
        "category": "📜 الاستقبال",
        "position": 2
      }
    ],
    "welcome_settings": {
      "enabled": true,
      "channel": "الترحيب",
      "message": "أهلاً وسهلاً {user} في {server}! 🎉",
      "use_embed": true,
      "title": "مرحباً بك! 🎉",
      "color": "#00ff00",
      "thumbnail": true,
      "footer": "نتمنى لك وقتاً ممتعاً معنا",
      "goodbye_enabled": true,
      "goodbye_channel": "الترحيب",
      "goodbye_message": "وداعاً {username}! نتمنى أن نراك قريباً 👋"
    },
    "auto_role_settings": {
      "enabled": true,
      "roles": ["👤 العضو"]
    }
  };

  useEffect(() => {
    fetchConfigs();
    fetchBotStatus();
    
    // Set up polling for bot status
    const statusInterval = setInterval(fetchBotStatus, 5000);
    return () => clearInterval(statusInterval);
  }, []);

  const fetchConfigs = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/configs`);
      setConfigs(response.data);
    } catch (error) {
      console.error('Error fetching configs:', error);
    }
  };

  const fetchBotStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/bot/status`);
      setBotStatus(response.data);
    } catch (error) {
      console.error('Error fetching bot status:', error);
    }
  };

  const handleCreateConfig = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      await axios.post(`${API_BASE_URL}/api/configs`, configForm);
      await fetchConfigs();
      setShowCreateForm(false);
      setConfigForm({
        name: '',
        description: '',
        icon_url: '',
        roles: [],
        channels: []
      });
      alert('تم إنشاء الإعداد بنجاح!');
    } catch (error) {
      console.error('Error creating config:', error);
      alert('حدث خطأ أثناء إنشاء الإعداد');
    } finally {
      setLoading(false);
    }
  };

  const handleJsonSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const parsedJson = JSON.parse(jsonInput);
      await axios.post(`${API_BASE_URL}/api/configs`, parsedJson);
      await fetchConfigs();
      setShowJsonEditor(false);
      setJsonInput('');
      alert('تم إنشاء الإعداد من JSON بنجاح!');
    } catch (error) {
      console.error('Error creating config from JSON:', error);
      if (error.message.includes('JSON')) {
        alert('خطأ في تنسيق JSON. تأكد من صحة التنسيق.');
      } else {
        alert('حدث خطأ أثناء إنشاء الإعداد');
      }
    } finally {
      setLoading(false);
    }
  };

  const deleteConfig = async (configId) => {
    if (window.confirm('هل أنت متأكد من حذف هذا الإعداد؟')) {
      try {
        await axios.delete(`${API_BASE_URL}/api/configs/${configId}`);
        await fetchConfigs();
        alert('تم حذف الإعداد بنجاح!');
      } catch (error) {
        console.error('Error deleting config:', error);
        alert('حدث خطأ أثناء حذف الإعداد');
      }
    }
  };

  const viewConfigDetails = (config) => {
    setSelectedConfig(config);
  };

  const startBot = async () => {
    try {
      await axios.post(`${API_BASE_URL}/api/bot/start`);
      alert('تم بدء تشغيل البوت!');
      setTimeout(fetchBotStatus, 2000);
    } catch (error) {
      console.error('Error starting bot:', error);
      alert('حدث خطأ أثناء تشغيل البوت');
    }
  };

  const loadJsonTemplate = () => {
    setJsonInput(JSON.stringify(defaultJsonTemplate, null, 2));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-cyan-50" dir="rtl">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            🤖 مدير سيرفرات Discord
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            أنشئ وأدر سيرفرات Discord تلقائياً باستخدام ملفات JSON المخصصة
          </p>
        </div>

        {/* Bot Status Card */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4 space-x-reverse">
              <div className={`w-4 h-4 rounded-full ${
                botStatus.connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`}></div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">حالة البوت</h3>
                <p className="text-sm text-gray-600">
                  {botStatus.connected ? '✅ متصل ويعمل' : '❌ غير متصل'}
                </p>
              </div>
            </div>
            {!botStatus.running && (
              <button
                onClick={startBot}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
              >
                تشغيل البوت
              </button>
            )}
          </div>
          {botStatus.last_error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-700 text-sm">خطأ: {botStatus.last_error}</p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-4 mb-8 justify-center">
          <button
            onClick={() => setShowCreateForm(true)}
            className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors flex items-center space-x-2 space-x-reverse"
          >
            <span>➕</span>
            <span>إنشاء إعداد جديد</span>
          </button>
          
          <button
            onClick={() => setShowJsonEditor(true)}
            className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors flex items-center space-x-2 space-x-reverse"
          >
            <span>📝</span>
            <span>رفع JSON</span>
          </button>
        </div>

        {/* Configurations Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {configs.map((config) => (
            <div key={config.id} className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-shadow">
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">{config.name}</h3>
                    <p className="text-gray-600 text-sm">{config.description}</p>
                  </div>
                </div>
                
                <div className="space-y-2 mb-4">
                  <div className="flex items-center text-sm text-gray-600">
                    <span className="ml-2">👥</span>
                    <span>{config.roles?.length || 0} أدوار</span>
                  </div>
                  <div className="flex items-center text-sm text-gray-600">
                    <span className="ml-2">📋</span>
                    <span>{config.channels?.length || 0} قنوات</span>
                  </div>
                  {config.welcome_settings?.enabled && (
                    <div className="flex items-center text-sm text-green-600">
                      <span className="ml-2">🎉</span>
                      <span>ترحيب مفعل</span>
                    </div>
                  )}
                  {config.auto_role_settings?.enabled && (
                    <div className="flex items-center text-sm text-blue-600">
                      <span className="ml-2">👤</span>
                      <span>أدوار تلقائية</span>
                    </div>
                  )}
                </div>
                
                <div className="flex space-x-2 space-x-reverse">
                  <button
                    onClick={() => viewConfigDetails(config)}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 px-3 rounded-lg text-sm transition-colors"
                  >
                    عرض التفاصيل
                  </button>
                  <button
                    onClick={() => deleteConfig(config.id)}
                    className="bg-red-600 hover:bg-red-700 text-white py-2 px-3 rounded-lg text-sm transition-colors"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Instructions Card */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-200">
          <h3 className="text-xl font-bold text-blue-900 mb-4">📋 كيفية الاستخدام</h3>
          <div className="space-y-3 text-blue-800">
            <div>
              <p><strong>1.</strong> أنشئ إعداد سيرفر جديد أو ارفع ملف JSON</p>
              <p><strong>2.</strong> تأكد من أن البوت متصل ويعمل</p>
              <p><strong>3.</strong> في Discord، استخدم الأوامر التالية:</p>
              
              <div className="mt-3 space-y-2 bg-blue-100 p-4 rounded-lg">
                <div>
                  <code className="bg-blue-200 px-2 py-1 rounded text-sm">/setup_server [اسم_الإعداد]</code>
                  <span className="mr-2 text-sm">- إعداد السيرفر تلقائياً</span>
                </div>
                <div>
                  <code className="bg-blue-200 px-2 py-1 rounded text-sm">/configure_welcome</code>
                  <span className="mr-2 text-sm">- إعداد رسائل الترحيب</span>
                </div>
                <div>
                  <code className="bg-blue-200 px-2 py-1 rounded text-sm">/configure_autorole</code>
                  <span className="mr-2 text-sm">- إعداد الأدوار التلقائية</span>
                </div>
                <div>
                  <code className="bg-blue-200 px-2 py-1 rounded text-sm">/test_welcome</code>
                  <span className="mr-2 text-sm">- اختبار رسالة الترحيب</span>
                </div>
                <div>
                  <code className="bg-blue-200 px-2 py-1 rounded text-sm">/list_configs</code>
                  <span className="mr-2 text-sm">- عرض الإعدادات المتاحة</span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
            <h4 className="font-semibold text-green-900 mb-2">🎉 الميزات الجديدة:</h4>
            <ul className="text-green-800 text-sm space-y-1">
              <li>• رسائل ترحيب تلقائية للأعضاء الجدد</li>
              <li>• توزيع أدوار تلقائي عند الانضمام</li>
              <li>• رسائل وداع عند مغادرة الأعضاء</li>
              <li>• تخصيص كامل لرسائل الترحيب والألوان</li>
              <li>• اختبار رسائل الترحيب قبل التفعيل</li>
            </ul>
          </div>
        </div>

        {/* Create Form Modal */}
        {showCreateForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-6">إنشاء إعداد جديد</h2>
                
                <form onSubmit={handleCreateConfig} className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">اسم السيرفر</label>
                    <input
                      type="text"
                      value={configForm.name}
                      onChange={(e) => setConfigForm({...configForm, name: e.target.value})}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">الوصف</label>
                    <textarea
                      value={configForm.description}
                      onChange={(e) => setConfigForm({...configForm, description: e.target.value})}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      rows="3"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">رابط الأيقونة (اختياري)</label>
                    <input
                      type="url"
                      value={configForm.icon_url}
                      onChange={(e) => setConfigForm({...configForm, icon_url: e.target.value})}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  
                  <div className="flex space-x-4 space-x-reverse pt-4">
                    <button
                      type="submit"
                      disabled={loading}
                      className="flex-1 bg-green-600 hover:bg-green-700 text-white py-3 px-4 rounded-lg font-semibold transition-colors disabled:opacity-50"
                    >
                      {loading ? 'جاري الإنشاء...' : 'إنشاء الإعداد'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowCreateForm(false)}
                      className="flex-1 bg-gray-500 hover:bg-gray-600 text-white py-3 px-4 rounded-lg font-semibold transition-colors"
                    >
                      إلغاء
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* JSON Editor Modal */}
        {showJsonEditor && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-6">رفع إعداد JSON</h2>
                
                <div className="mb-4">
                  <button
                    onClick={loadJsonTemplate}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm transition-colors"
                  >
                    تحميل القالب الافتراضي
                  </button>
                </div>
                
                <form onSubmit={handleJsonSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">محتوى JSON</label>
                    <textarea
                      value={jsonInput}
                      onChange={(e) => setJsonInput(e.target.value)}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                      rows="20"
                      placeholder="ألصق محتوى JSON هنا..."
                      required
                    />
                  </div>
                  
                  <div className="flex space-x-4 space-x-reverse pt-4">
                    <button
                      type="submit"
                      disabled={loading}
                      className="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-3 px-4 rounded-lg font-semibold transition-colors disabled:opacity-50"
                    >
                      {loading ? 'جاري الإنشاء...' : 'إنشاء من JSON'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowJsonEditor(false)}
                      className="flex-1 bg-gray-500 hover:bg-gray-600 text-white py-3 px-4 rounded-lg font-semibold transition-colors"
                    >
                      إلغاء
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* Config Details Modal */}
        {selectedConfig && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex items-start justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">{selectedConfig.name}</h2>
                    <p className="text-gray-600">{selectedConfig.description}</p>
                  </div>
                  <button
                    onClick={() => setSelectedConfig(null)}
                    className="text-gray-500 hover:text-gray-700 text-xl font-bold"
                  >
                    ✕
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Roles */}
                  <div>
                    <h3 className="text-lg font-bold text-gray-900 mb-4">👥 الأدوار ({selectedConfig.roles?.length || 0})</h3>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {selectedConfig.roles?.map((role, index) => (
                        <div key={index} className="bg-gray-50 p-3 rounded-lg">
                          <div className="flex items-center space-x-2 space-x-reverse">
                            <div 
                              className="w-4 h-4 rounded-full" 
                              style={{backgroundColor: role.color}}
                            ></div>
                            <span className="font-medium">{role.name}</span>
                          </div>
                          <div className="text-xs text-gray-600 mt-1">
                            صلاحيات: {role.permissions} | مميز: {role.hoist ? 'نعم' : 'لا'}
                          </div>
                        </div>
                      )) || <p className="text-gray-500">لا توجد أدوار</p>}
                    </div>
                  </div>
                  
                  {/* Channels */}
                  <div>
                    <h3 className="text-lg font-bold text-gray-900 mb-4">📋 القنوات ({selectedConfig.channels?.length || 0})</h3>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {selectedConfig.channels?.map((channel, index) => (
                        <div key={index} className="bg-gray-50 p-3 rounded-lg">
                          <div className="flex items-center space-x-2 space-x-reverse">
                            <span className="text-sm">
                              {channel.type === 'category' ? '📁' : 
                               channel.type === 'voice' ? '🎙️' : '💬'}
                            </span>
                            <span className="font-medium">{channel.name}</span>
                          </div>
                          <div className="text-xs text-gray-600 mt-1">
                            نوع: {channel.type} {channel.category && `| تصنيف: ${channel.category}`}
                          </div>
                        </div>
                      )) || <p className="text-gray-500">لا توجد قنوات</p>}
                    </div>
                  </div>
                </div>
                
                <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-semibold text-blue-900 mb-2">كيفية الاستخدام:</h4>
                  <p className="text-blue-800 text-sm">
                    استخدم الأمر <code className="bg-blue-100 px-2 py-1 rounded">/setup_server {selectedConfig.name}</code> في Discord لإعداد السيرفر
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;