import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import apiClient from '../services/api';

const NotificationSettingsPage = () => {
    const { user } = useAuth();
    const [preferences, setPreferences] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');

    // Categories de notifications avec leurs labels
    const categories = {
        admin_action: 'Actions administratives',
        rent_payment: 'Paiements de loyer',
        lease_events: 'Événements de bail',
        property_updates: 'Mises à jour propriétés',
        maintenance: 'Maintenance',
        financial: 'Finances',
        legal: 'Légal',
        system: 'Système',
        marketing: 'Marketing'
    };

    // Canaux de notification
    const channels = {
        in_app: 'Notifications dans l\'app',
        email: 'Email',
        sms: 'SMS',
        push: 'Notifications push'
    };

    useEffect(() => {
        loadPreferences();
    }, []);

    const loadPreferences = async () => {
        try {
            const response = await apiClient.get('/notifications/preferences');
            setPreferences(response.data);
        } catch (error) {
            console.error('Erreur chargement préférences:', error);
            setMessage('Erreur lors du chargement des préférences');
        } finally {
            setLoading(false);
        }
    };

    const savePreferences = async () => {
        setSaving(true);
        try {
            await apiClient.put('/notifications/preferences', preferences);
            setMessage('Préférences sauvegardées avec succès');
            setTimeout(() => setMessage(''), 3000);
        } catch (error) {
            console.error('Erreur sauvegarde:', error);
            setMessage('Erreur lors de la sauvegarde');
        } finally {
            setSaving(false);
        }
    };

    const sendTestNotification = async () => {
        try {
            await apiClient.post('/notifications/test', {
                category: 'system',
                channels: ['in_app']
            });
            setMessage('Notification de test envoyée');
            setTimeout(() => setMessage(''), 3000);
        } catch (error) {
            console.error('Erreur test notification:', error);
            setMessage('Erreur lors de l\'envoi du test');
        }
    };

    const updateGlobalSetting = (key, value) => {
        setPreferences(prev => ({
            ...prev,
            global_settings: {
                ...prev.global_settings,
                [key]: value
            }
        }));
    };

    const updateQuietHours = (key, value) => {
        setPreferences(prev => ({
            ...prev,
            quiet_hours: {
                ...prev.quiet_hours,
                [key]: value
            }
        }));
    };

    const updateContactInfo = (key, value) => {
        setPreferences(prev => ({
            ...prev,
            contact_info: {
                ...prev.contact_info,
                [key]: value
            }
        }));
    };

    const updateCategoryChannels = (category, channels) => {
        setPreferences(prev => ({
            ...prev,
            category_channels: {
                ...prev.category_channels,
                [category]: channels
            }
        }));
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600">Chargement des préférences...</p>
                </div>
            </div>
        );
    }

    if (!preferences) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center text-red-600">
                    <p>Erreur lors du chargement des préférences de notification</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="bg-white shadow rounded-lg">
                    {/* Header */}
                    <div className="px-6 py-4 border-b border-gray-200">
                        <h1 className="text-2xl font-bold text-gray-900">
                            🔔 Configuration des Notifications
                        </h1>
                        <p className="mt-1 text-sm text-gray-600">
                            Personnalisez vos préférences de notification pour rester informé selon vos besoins.
                        </p>
                    </div>

                    {/* Message de feedback */}
                    {message && (
                        <div className={`mx-6 mt-4 p-3 rounded-md text-sm ${
                            message.includes('succès') 
                                ? 'bg-green-50 text-green-800 border border-green-200' 
                                : 'bg-red-50 text-red-800 border border-red-200'
                        }`}>
                            {message}
                        </div>
                    )}

                    <div className="p-6 space-y-8">
                        {/* Paramètres globaux */}
                        <section>
                            <h2 className="text-lg font-medium text-gray-900 mb-4">
                                ⚙️ Paramètres Généraux
                            </h2>
                            <div className="space-y-4">
                                <label className="flex items-center">
                                    <input
                                        type="checkbox"
                                        checked={preferences.global_settings.notifications_enabled}
                                        onChange={(e) => updateGlobalSetting('notifications_enabled', e.target.checked)}
                                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                    />
                                    <span className="ml-3 text-sm text-gray-900">
                                        Activer toutes les notifications
                                    </span>
                                </label>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <label className="flex items-center">
                                        <input
                                            type="checkbox"
                                            checked={preferences.global_settings.email_notifications}
                                            onChange={(e) => updateGlobalSetting('email_notifications', e.target.checked)}
                                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                            disabled={!preferences.global_settings.notifications_enabled}
                                        />
                                        <span className="ml-3 text-sm text-gray-700">
                                            📧 Notifications par email
                                        </span>
                                    </label>

                                    <label className="flex items-center">
                                        <input
                                            type="checkbox"
                                            checked={preferences.global_settings.sms_notifications}
                                            onChange={(e) => updateGlobalSetting('sms_notifications', e.target.checked)}
                                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                            disabled={!preferences.global_settings.notifications_enabled}
                                        />
                                        <span className="ml-3 text-sm text-gray-700">
                                            📱 Notifications SMS
                                        </span>
                                    </label>

                                    <label className="flex items-center">
                                        <input
                                            type="checkbox"
                                            checked={preferences.global_settings.push_notifications}
                                            onChange={(e) => updateGlobalSetting('push_notifications', e.target.checked)}
                                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                            disabled={!preferences.global_settings.notifications_enabled}
                                        />
                                        <span className="ml-3 text-sm text-gray-700">
                                            🔔 Notifications push
                                        </span>
                                    </label>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Fréquence des résumés
                                    </label>
                                    <select
                                        value={preferences.global_settings.digest_frequency}
                                        onChange={(e) => updateGlobalSetting('digest_frequency', e.target.value)}
                                        className="block w-full md:w-64 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    >
                                        <option value="immediate">Immédiat</option>
                                        <option value="daily_digest">Résumé quotidien</option>
                                        <option value="weekly_digest">Résumé hebdomadaire</option>
                                        <option value="monthly_digest">Résumé mensuel</option>
                                    </select>
                                </div>
                            </div>
                        </section>

                        {/* Heures silencieuses */}
                        <section>
                            <h2 className="text-lg font-medium text-gray-900 mb-4">
                                🌙 Heures Silencieuses
                            </h2>
                            <div className="space-y-4">
                                <label className="flex items-center">
                                    <input
                                        type="checkbox"
                                        checked={preferences.quiet_hours.enabled}
                                        onChange={(e) => updateQuietHours('enabled', e.target.checked)}
                                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                    />
                                    <span className="ml-3 text-sm text-gray-900">
                                        Activer les heures silencieuses (pas de notifications)
                                    </span>
                                </label>

                                {preferences.quiet_hours.enabled && (
                                    <div className="ml-7 grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Début
                                            </label>
                                            <input
                                                type="time"
                                                value={preferences.quiet_hours.start}
                                                onChange={(e) => updateQuietHours('start', e.target.value)}
                                                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Fin
                                            </label>
                                            <input
                                                type="time"
                                                value={preferences.quiet_hours.end}
                                                onChange={(e) => updateQuietHours('end', e.target.value)}
                                                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>
                        </section>

                        {/* Informations de contact */}
                        <section>
                            <h2 className="text-lg font-medium text-gray-900 mb-4">
                                📞 Informations de Contact
                            </h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Email alternatif (optionnel)
                                    </label>
                                    <input
                                        type="email"
                                        value={preferences.contact_info.email_address || ''}
                                        onChange={(e) => updateContactInfo('email_address', e.target.value)}
                                        placeholder="email@exemple.com"
                                        className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Numéro de téléphone (pour SMS)
                                    </label>
                                    <input
                                        type="tel"
                                        value={preferences.contact_info.phone_number || ''}
                                        onChange={(e) => updateContactInfo('phone_number', e.target.value)}
                                        placeholder="+33 6 12 34 56 78"
                                        className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    />
                                </div>
                            </div>
                        </section>

                        {/* Configuration par catégorie */}
                        <section>
                            <h2 className="text-lg font-medium text-gray-900 mb-4">
                                📋 Préférences par Catégorie
                            </h2>
                            <div className="space-y-6">
                                {Object.entries(categories).map(([categoryKey, categoryLabel]) => (
                                    <div key={categoryKey} className="border border-gray-200 rounded-lg p-4">
                                        <h3 className="font-medium text-gray-900 mb-3">
                                            {categoryLabel}
                                        </h3>
                                        <div className="space-y-2">
                                            {Object.entries(channels).map(([channelKey, channelLabel]) => {
                                                const isChannelActive = preferences.category_channels[categoryKey]?.includes(channelKey);
                                                const isChannelAvailable = 
                                                    (channelKey === 'in_app') ||
                                                    (channelKey === 'email' && preferences.global_settings.email_notifications) ||
                                                    (channelKey === 'sms' && preferences.global_settings.sms_notifications) ||
                                                    (channelKey === 'push' && preferences.global_settings.push_notifications);

                                                return (
                                                    <label key={channelKey} className="flex items-center">
                                                        <input
                                                            type="checkbox"
                                                            checked={isChannelActive}
                                                            disabled={!isChannelAvailable}
                                                            onChange={(e) => {
                                                                const currentChannels = preferences.category_channels[categoryKey] || [];
                                                                const newChannels = e.target.checked 
                                                                    ? [...currentChannels, channelKey]
                                                                    : currentChannels.filter(ch => ch !== channelKey);
                                                                updateCategoryChannels(categoryKey, newChannels);
                                                            }}
                                                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                                        />
                                                        <span className={`ml-3 text-sm ${
                                                            isChannelAvailable ? 'text-gray-700' : 'text-gray-400'
                                                        }`}>
                                                            {channelLabel}
                                                        </span>
                                                    </label>
                                                );
                                            })}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>

                        {/* Actions */}
                        <section className="border-t pt-6">
                            <div className="flex flex-col sm:flex-row gap-4">
                                <button
                                    onClick={savePreferences}
                                    disabled={saving}
                                    className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {saving ? 'Sauvegarde...' : '💾 Sauvegarder les Préférences'}
                                </button>
                                
                                <button
                                    onClick={sendTestNotification}
                                    className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
                                >
                                    🧪 Envoyer une Notification de Test
                                </button>
                                
                                <button
                                    onClick={loadPreferences}
                                    className="bg-gray-600 text-white px-6 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
                                >
                                    🔄 Recharger
                                </button>
                            </div>
                        </section>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default NotificationSettingsPage;