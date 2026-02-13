import { useState, useCallback } from 'react';
import { User } from 'firebase/auth';

export interface ExplorationItem {
    id: string;
    title: string;
    url?: string;
    pdf_url?: string;
    summary?: string;
    isArchived?: boolean;
    localAssetPath?: string;
    localAssetType?: string;
    // Add other fields
    [key: string]: any;
}

export const useExploration = (user: User | null) => {
    const [items, setItems] = useState<ExplorationItem[]>([]);
    const [loading, setLoading] = useState(false);

    const fetchItems = useCallback(async () => {
        if (!user) return;
        setLoading(true);
        try {
            const token = await user.getIdToken();
            const res = await fetch('/api/exploration', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setItems(data.items || []);
            }
        } catch (e) {
            console.error("Failed to fetch exploration items", e);
        } finally {
            setLoading(false);
        }
    }, [user]);

    const saveItem = async (item: any, sourceRadarId?: string) => {
        if (!user) return false;
        try {
            const token = await user.getIdToken();
            const response = await fetch('/api/exploration/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    ...item,
                    savedAt: new Date().toISOString(),
                    sourceRadarId
                })
            });
            if (response.ok) {
                // Refresh items immediately
                fetchItems();
                return true;
            }
            return false;
        } catch (error) {
            console.error("Error saving to exploration:", error);
            return false;
        }
    };

    const deleteItem = async (id: string) => {
        if (!user) return false;
        try {
            const token = await user.getIdToken();
            const response = await fetch(`/api/exploration/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                setItems(prev => prev.filter(item => item.id !== id));
                return true;
            }
            return false;
        } catch (error) {
            console.error("Error deleting exploration item:", error);
            return false;
        }
    };

    const archiveItem = async (id: string, archived: boolean) => {
        if (!user) return false;
        try {
            const token = await user.getIdToken();
            const response = await fetch(`/api/exploration/${id}/archive?archived=${archived}`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                setItems(prev => prev.map(item =>
                    item.id === id ? { ...item, isArchived: archived } : item
                ));
                return true;
            }
            return false;
        } catch (error) {
            console.error("Error archiving item:", error);
            return false;
        }
    };

    const manualAdd = async (mode: 'url' | 'upload', title: string, url?: string, file?: File) => {
        if (!user) return false;

        try {
            const token = await user.getIdToken();
            let response;

            if (mode === 'url') {
                response = await fetch('/api/exploration/save', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        title: title || 'New Resource',
                        url: url,
                        summary: 'Added manually',
                        savedAt: new Date().toISOString()
                    })
                });
            } else {
                const formData = new FormData();
                formData.append('title', title || (file ? file.name : 'Uploaded File'));
                if (file) {
                    formData.append('file', file);
                }

                response = await fetch('/api/exploration/upload', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });
            }

            if (response.ok) {
                fetchItems();
                return true;
            }
            return false;
        } catch (error) {
            console.error("Error adding item:", error);
            return false;
        }
    };

    return { items, loading, fetchItems, saveItem, deleteItem, archiveItem, manualAdd, setItems };
};
