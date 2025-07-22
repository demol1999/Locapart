import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import apiClient from '../services/api';

const NotificationBell = () => {
    const { user } = useAuth();
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [isOpen, setIsOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const dropdownRef = useRef(null);

    useEffect(() => {
        if (user) {
            loadNotifications();
            // Actualiser toutes les 30 secondes
            const interval = setInterval(loadNotifications, 30000);
            return () => clearInterval(interval);
        }
    }, [user]);

    // Fermer le dropdown si on clique dehors
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const loadNotifications = async () => {
        try {
            // Charger le résumé pour la cloche
            const summaryResponse = await apiClient.get('/audit/notifications/summary');
            const summary = summaryResponse.data;
            
            setUnreadCount(summary.unread_count || 0);

            // Si le dropdown est ouvert, charger les notifications détaillées
            if (isOpen) {
                const notificationsResponse = await apiClient.get('/audit/notifications?limit=10');
                setNotifications(notificationsResponse.data.notifications || []);
            }
        } catch (error) {
            console.error('Erreur chargement notifications:', error);
        }
    };

    const toggleDropdown = async () => {
        if (!isOpen) {
            setLoading(true);
            try {
                const response = await apiClient.get('/audit/notifications?limit=10');
                setNotifications(response.data.notifications || []);
            } catch (error) {
                console.error('Erreur chargement notifications:', error);
            } finally {
                setLoading(false);
            }
        }
        setIsOpen(!isOpen);
    };

    const markAsRead = async (notificationIds) => {
        try {
            await apiClient.post('/audit/notifications/mark-read', {
                notification_ids: notificationIds
            });
            
            // Mettre à jour l'état local
            setNotifications(prev => 
                prev.map(notif => 
                    notificationIds.includes(notif.id) 
                        ? { ...notif, is_read: true }
                        : notif
                )
            );
            
            // Recalculer le nombre non lus
            const newUnreadCount = notifications.filter(n => 
                !n.is_read && !notificationIds.includes(n.id)
            ).length;
            setUnreadCount(Math.max(0, newUnreadCount));
            
        } catch (error) {
            console.error('Erreur marquage lu:', error);
        }
    };

    const markAllAsRead = async () => {
        try {
            await apiClient.post('/audit/notifications/mark-read', {
                mark_all: true
            });
            
            setNotifications(prev => prev.map(notif => ({ ...notif, is_read: true })));
            setUnreadCount(0);
        } catch (error) {
            console.error('Erreur marquage tout lu:', error);
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
            'low': 'text-gray-500',
            'normal': 'text-blue-500',
            'high': 'text-orange-500',
            'urgent': 'text-red-500',
            'critical': 'text-red-700'
        };
        return colors[priority] || 'text-gray-500';
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

    if (!user) return null;

    return (
        <div className="relative" ref={dropdownRef}>
            {/* Cloche */}
            <button
                onClick={toggleDropdown}
                className="relative p-2 text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-md"
            >
                <span className="sr-only">Notifications</span>
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5-5V9a6 6 0 10-12 0v3l-5 5h5a3 3 0 106 0z" />
                </svg>
                
                {/* Badge nombre non lues */}
                {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-500 rounded-full min-w-[1.25rem] h-5">
                        {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                )}
            </button>

            {/* Dropdown */}
            {isOpen && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
                    {/* Header */}
                    <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                        <h3 className="text-sm font-medium text-gray-900">
                            🔔 Notifications {unreadCount > 0 && `(${unreadCount} non lues)`}
                        </h3>
                        
                        {unreadCount > 0 && (
                            <button
                                onClick={markAllAsRead}
                                className="text-xs text-blue-600 hover:text-blue-800"
                            >
                                Tout marquer lu
                            </button>
                        )}
                    </div>

                    {/* Liste des notifications */}
                    <div className="max-h-96 overflow-y-auto">
                        {loading ? (
                            <div className="p-4 text-center">
                                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
                                <p className="text-xs text-gray-500 mt-2">Chargement...</p>
                            </div>
                        ) : notifications.length === 0 ? (
                            <div className="p-6 text-center text-gray-500">
                                <span className="text-2xl mb-2 block">📭</span>
                                <p className="text-sm">Aucune notification</p>
                            </div>
                        ) : (
                            <div className="divide-y divide-gray-100">
                                {notifications.map((notification) => (
                                    <div
                                        key={notification.id}
                                        className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                                            !notification.is_read ? 'bg-blue-50' : ''
                                        }`}
                                        onClick={() => !notification.is_read && markAsRead([notification.id])}
                                    >
                                        <div className="flex items-start space-x-3">
                                            <div className={`flex-shrink-0 text-lg ${getPriorityColor(notification.priority)}`}>
                                                {getNotificationIcon(notification.notification_type)}
                                            </div>
                                            
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center justify-between">
                                                    <p className={`text-sm font-medium ${
                                                        !notification.is_read ? 'text-gray-900' : 'text-gray-700'
                                                    }`}>
                                                        {notification.title}
                                                    </p>
                                                    
                                                    {!notification.is_read && (
                                                        <div className="flex-shrink-0 w-2 h-2 bg-blue-600 rounded-full"></div>
                                                    )}
                                                </div>
                                                
                                                <p className={`text-xs mt-1 ${
                                                    !notification.is_read ? 'text-gray-700' : 'text-gray-500'
                                                }`}>
                                                    {notification.message}
                                                </p>
                                                
                                                <div className="flex items-center justify-between mt-2">
                                                    <span className="text-xs text-gray-400">
                                                        {formatTimeAgo(notification.created_at)}
                                                    </span>
                                                    
                                                    {notification.priority !== 'normal' && (
                                                        <span className={`text-xs font-medium ${getPriorityColor(notification.priority)}`}>
                                                            {notification.priority.toUpperCase()}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    {notifications.length > 0 && (
                        <div className="px-4 py-3 border-t border-gray-200 text-center">
                            <a
                                href="/notifications"
                                className="text-sm text-blue-600 hover:text-blue-800"
                            >
                                Voir toutes les notifications →
                            </a>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default NotificationBell;