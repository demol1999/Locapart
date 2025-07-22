import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import apiClient from '../services/api';

const NotificationsPage = () => {
    const { user } = useAuth();
    const [notifications, setNotifications] = useState([]);
    const [queueStatus, setQueueStatus] = useState(null);
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('notifications');
    const [filters, setFilters] = useState({
        unread_only: false,
        limit: 20
    });

    const tabs = [
        { id: 'notifications', label: '📋 Notifications', icon: '📋' },
        { id: 'queue', label: '⏳ File d\'attente', icon: '⏳' },
        { id: 'settings', label: '⚙️ Paramètres', icon: '⚙️' },
        { id: 'analytics', label: '📊 Statistiques', icon: '📊' }
    ];

    useEffect(() => {
        if (user) {
            loadData();
        }
    }, [user, activeTab]);

    const loadData = async () => {
        setLoading(true);
        try {
            switch (activeTab) {
                case 'notifications':
                    await loadNotifications();
                    break;
                case 'queue':
                    await loadQueueStatus();
                    break;
                case 'analytics':
                    await loadAnalytics();
                    break;
                default:
                    break;
            }
        } catch (error) {
            console.error('Erreur chargement données:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadNotifications = async () => {
        const response = await apiClient.get('/audit/notifications', { params: filters });
        setNotifications(response.data.notifications || []);
    };

    const loadQueueStatus = async () => {
        const response = await apiClient.get('/notifications/queue/status');
        setQueueStatus(response.data);
    };

    const loadAnalytics = async () => {
        const response = await apiClient.get('/notifications/analytics?days=30');
        setAnalytics(response.data);
    };

    const markAsRead = async (notificationIds) => {
        try {
            await apiClient.post('/audit/notifications/mark-read', {
                notification_ids: notificationIds
            });
            
            setNotifications(prev => 
                prev.map(notif => 
                    notificationIds.includes(notif.id) 
                        ? { ...notif, is_read: true, read_at: new Date().toISOString() }
                        : notif
                )
            );
        } catch (error) {
            console.error('Erreur marquage lu:', error);
        }
    };

    const archiveNotifications = async (olderThanDays = 30) => {
        try {
            await apiClient.post('/audit/notifications/archive', {
                archive_read: true,
                older_than_days: olderThanDays
            });
            
            // Recharger les notifications
            await loadNotifications();
        } catch (error) {
            console.error('Erreur archivage:', error);
        }
    };

    const getNotificationIcon = (type) => {
        const icons = {
            'admin_action': '🔧',
            'undo_performed': '🔄',
            'system_alert': '⚙️',
            'account_update': 'ℹ️',
            'security_alert': '🛡️'
        };
        return icons[type] || '🔔';
    };

    const getPriorityColor = (priority) => {
        const colors = {
            'low': 'border-gray-200 bg-gray-50',
            'normal': 'border-blue-200 bg-blue-50',
            'high': 'border-orange-200 bg-orange-50',
            'urgent': 'border-red-200 bg-red-50',
            'critical': 'border-red-400 bg-red-100'
        };
        return colors[priority] || 'border-gray-200 bg-gray-50';
    };

    const formatTimeAgo = (dateString) => {
        const now = new Date();
        const date = new Date(dateString);
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'À l\'instant';
        if (diffMins < 60) return `Il y a ${diffMins} min`;
        if (diffHours < 24) return `Il y a ${diffHours}h`;
        if (diffDays < 7) return `Il y a ${diffDays} jour(s)`;
        return date.toLocaleDateString('fr-FR');
    };

    const renderNotificationsTab = () => (
        <div className="space-y-6">
            {/* Filtres */}
            <div className="bg-gray-50 p-4 rounded-lg">
                <div className="flex flex-wrap gap-4 items-center">
                    <label className="flex items-center">
                        <input
                            type="checkbox"
                            checked={filters.unread_only}
                            onChange={(e) => setFilters(prev => ({ ...prev, unread_only: e.target.checked }))}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <span className="ml-2 text-sm text-gray-700">Non lues seulement</span>
                    </label>
                    
                    <select
                        value={filters.limit}
                        onChange={(e) => setFilters(prev => ({ ...prev, limit: parseInt(e.target.value) }))}
                        className="px-3 py-1 border border-gray-300 rounded-md text-sm"
                    >
                        <option value={10}>10 par page</option>
                        <option value={20}>20 par page</option>
                        <option value={50}>50 par page</option>
                    </select>
                    
                    <button
                        onClick={() => archiveNotifications()}
                        className="px-3 py-1 bg-gray-600 text-white rounded-md text-sm hover:bg-gray-700"
                    >
                        🗄️ Archiver les anciennes
                    </button>
                </div>
            </div>

            {/* Liste des notifications */}
            {loading ? (
                <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-2 text-gray-600">Chargement...</p>
                </div>
            ) : notifications.length === 0 ? (
                <div className="text-center py-12">
                    <span className="text-4xl mb-4 block">📭</span>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Aucune notification</h3>
                    <p className="text-gray-600">Vous n'avez pas de notifications pour le moment.</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {notifications.map((notification) => (
                        <div
                            key={notification.id}
                            className={`border rounded-lg p-4 transition-all hover:shadow-md ${
                                getPriorityColor(notification.priority)
                            } ${!notification.is_read ? 'border-l-4 border-l-blue-500' : ''}`}
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex items-start space-x-3 flex-1">
                                    <div className="text-xl">
                                        {getNotificationIcon(notification.notification_type)}
                                    </div>
                                    
                                    <div className="flex-1">
                                        <div className="flex items-center justify-between mb-1">
                                            <h4 className={`font-medium ${
                                                !notification.is_read ? 'text-gray-900' : 'text-gray-700'
                                            }`}>
                                                {notification.title}
                                            </h4>
                                            
                                            <div className="flex items-center space-x-2">
                                                {notification.priority !== 'normal' && (
                                                    <span className={`text-xs font-medium px-2 py-1 rounded ${
                                                        notification.priority === 'urgent' ? 'bg-red-100 text-red-800' :
                                                        notification.priority === 'high' ? 'bg-orange-100 text-orange-800' :
                                                        'bg-gray-100 text-gray-800'
                                                    }`}>
                                                        {notification.priority.toUpperCase()}
                                                    </span>
                                                )}
                                                
                                                {!notification.is_read && (
                                                    <button
                                                        onClick={() => markAsRead([notification.id])}
                                                        className="text-xs text-blue-600 hover:text-blue-800"
                                                    >
                                                        Marquer lu
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                        
                                        <p className={`text-sm mb-2 ${
                                            !notification.is_read ? 'text-gray-700' : 'text-gray-600'
                                        }`}>
                                            {notification.message}
                                        </p>
                                        
                                        <div className="flex items-center justify-between text-xs text-gray-500">
                                            <span>{formatTimeAgo(notification.created_at)}</span>
                                            {notification.is_read && notification.read_at && (
                                                <span>Lu le {new Date(notification.read_at).toLocaleDateString('fr-FR')}</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );

    const renderQueueTab = () => (
        <div className="space-y-6">
            {loading ? (
                <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-2 text-gray-600">Chargement...</p>
                </div>
            ) : queueStatus ? (
                <>
                    {/* Statistiques de la queue */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <div className="bg-white p-6 rounded-lg shadow border">
                            <div className="flex items-center">
                                <div className="p-2 bg-blue-100 rounded-lg">
                                    <span className="text-xl">📤</span>
                                </div>
                                <div className="ml-4">
                                    <p className="text-sm font-medium text-gray-600">Total</p>
                                    <p className="text-2xl font-bold text-gray-900">{queueStatus.queue_stats.total}</p>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white p-6 rounded-lg shadow border">
                            <div className="flex items-center">
                                <div className="p-2 bg-yellow-100 rounded-lg">
                                    <span className="text-xl">⏳</span>
                                </div>
                                <div className="ml-4">
                                    <p className="text-sm font-medium text-gray-600">En attente</p>
                                    <p className="text-2xl font-bold text-gray-900">{queueStatus.queue_stats.pending || 0}</p>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white p-6 rounded-lg shadow border">
                            <div className="flex items-center">
                                <div className="p-2 bg-green-100 rounded-lg">
                                    <span className="text-xl">✅</span>
                                </div>
                                <div className="ml-4">
                                    <p className="text-sm font-medium text-gray-600">Envoyées</p>
                                    <p className="text-2xl font-bold text-gray-900">{queueStatus.queue_stats.sent || 0}</p>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white p-6 rounded-lg shadow border">
                            <div className="flex items-center">
                                <div className="p-2 bg-red-100 rounded-lg">
                                    <span className="text-xl">❌</span>
                                </div>
                                <div className="ml-4">
                                    <p className="text-sm font-medium text-gray-600">Échecs</p>
                                    <p className="text-2xl font-bold text-gray-900">{queueStatus.queue_stats.failed || 0}</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Prochaines notifications */}
                    {queueStatus.upcoming_notifications && queueStatus.upcoming_notifications.length > 0 && (
                        <div className="bg-white rounded-lg shadow border">
                            <div className="px-6 py-4 border-b border-gray-200">
                                <h3 className="text-lg font-medium text-gray-900">⏰ Prochaines Notifications</h3>
                            </div>
                            <div className="p-6">
                                <div className="space-y-4">
                                    {queueStatus.upcoming_notifications.map((notif) => (
                                        <div key={notif.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                            <div>
                                                <p className="font-medium text-gray-900">{notif.subject}</p>
                                                <p className="text-sm text-gray-600">Canal: {notif.channel}</p>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-sm text-gray-900">
                                                    {new Date(notif.scheduled_at).toLocaleString('fr-FR')}
                                                </p>
                                                <p className="text-xs text-gray-500">{notif.category}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </>
            ) : (
                <div className="text-center py-12">
                    <p className="text-gray-600">Aucune information de queue disponible</p>
                </div>
            )}
        </div>
    );

    const renderAnalyticsTab = () => (
        <div className="space-y-6">
            {loading ? (
                <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-2 text-gray-600">Chargement...</p>
                </div>
            ) : analytics ? (
                <>
                    {/* Métriques globales */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="bg-white p-6 rounded-lg shadow border">
                            <div className="text-center">
                                <p className="text-3xl font-bold text-blue-600">{analytics.total_notifications}</p>
                                <p className="text-sm text-gray-600">Total (30 jours)</p>
                            </div>
                        </div>

                        <div className="bg-white p-6 rounded-lg shadow border">
                            <div className="text-center">
                                <p className="text-3xl font-bold text-green-600">{analytics.successful_notifications}</p>
                                <p className="text-sm text-gray-600">Délivrées</p>
                            </div>
                        </div>

                        <div className="bg-white p-6 rounded-lg shadow border">
                            <div className="text-center">
                                <p className="text-3xl font-bold text-orange-600">{analytics.success_rate}%</p>
                                <p className="text-sm text-gray-600">Taux de succès</p>
                            </div>
                        </div>
                    </div>

                    {/* Répartition par catégorie */}
                    {analytics.category_breakdown && (
                        <div className="bg-white rounded-lg shadow border">
                            <div className="px-6 py-4 border-b border-gray-200">
                                <h3 className="text-lg font-medium text-gray-900">📊 Répartition par Catégorie</h3>
                            </div>
                            <div className="p-6">
                                <div className="space-y-4">
                                    {Object.entries(analytics.category_breakdown).map(([category, count]) => (
                                        <div key={category} className="flex items-center justify-between">
                                            <span className="text-sm font-medium text-gray-700 capitalize">
                                                {category.replace('_', ' ')}
                                            </span>
                                            <span className="text-sm text-gray-900">{count}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Répartition par canal */}
                    {analytics.channel_breakdown && (
                        <div className="bg-white rounded-lg shadow border">
                            <div className="px-6 py-4 border-b border-gray-200">
                                <h3 className="text-lg font-medium text-gray-900">📱 Répartition par Canal</h3>
                            </div>
                            <div className="p-6">
                                <div className="space-y-4">
                                    {Object.entries(analytics.channel_breakdown).map(([channel, count]) => (
                                        <div key={channel} className="flex items-center justify-between">
                                            <span className="text-sm font-medium text-gray-700 capitalize">
                                                {channel === 'in_app' ? 'Dans l\'app' : 
                                                 channel === 'email' ? 'Email' :
                                                 channel === 'sms' ? 'SMS' : channel}
                                            </span>
                                            <span className="text-sm text-gray-900">{count}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </>
            ) : (
                <div className="text-center py-12">
                    <p className="text-gray-600">Aucune donnée d'analytics disponible</p>
                </div>
            )}
        </div>
    );

    const renderSettingsTab = () => (
        <div className="bg-white rounded-lg shadow border p-6">
            <div className="text-center">
                <h3 className="text-lg font-medium text-gray-900 mb-4">⚙️ Paramètres de Notifications</h3>
                <p className="text-gray-600 mb-6">
                    Configurez vos préférences de notification en détail.
                </p>
                <a
                    href="/notification-settings"
                    className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                    🔧 Aller aux Paramètres Avancés
                </a>
            </div>
        </div>
    );

    if (!user) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <p className="text-gray-600">Veuillez vous connecter pour voir vos notifications.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900">🔔 Mes Notifications</h1>
                    <p className="mt-2 text-gray-600">
                        Gérez toutes vos notifications et préférences en un seul endroit.
                    </p>
                </div>

                {/* Tabs */}
                <div className="bg-white rounded-lg shadow border mb-6">
                    <div className="border-b border-gray-200">
                        <nav className="flex space-x-8 px-6" aria-label="Tabs">
                            {tabs.map((tab) => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`py-4 px-1 border-b-2 font-medium text-sm ${
                                        activeTab === tab.id
                                            ? 'border-blue-500 text-blue-600'
                                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                                >
                                    {tab.label}
                                </button>
                            ))}
                        </nav>
                    </div>

                    <div className="p-6">
                        {activeTab === 'notifications' && renderNotificationsTab()}
                        {activeTab === 'queue' && renderQueueTab()}
                        {activeTab === 'analytics' && renderAnalyticsTab()}
                        {activeTab === 'settings' && renderSettingsTab()}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default NotificationsPage;