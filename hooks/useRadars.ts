import { useState, useCallback } from 'react';
import { User } from 'firebase/auth';

export interface Radar {
    id: string;
    title: string;
    outputMedia?: string;
}

export interface RadarItem {
    id: string;
    title: string;
    url?: string;
    summary?: string;
    asset_type?: string;
    asset_url?: string;
    timestamp?: string;
    parent?: string; // If it's a summary
    // Add other fields from API response if necessary
    [key: string]: any;
}

export const useRadars = (user: User | null) => {
    const [radars, setRadars] = useState<Radar[]>([]);
    const [items, setItems] = useState<RadarItem[]>([]);
    const [loadingItems, setLoadingItems] = useState(false);

    // Fetch list of radars
    const fetchRadars = useCallback(async () => {
        if (!user) return;
        try {
            const token = await user.getIdToken();
            const res = await fetch('/api/radars', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setRadars(data.map((r: any) => ({
                    id: r.id,
                    title: r.title,
                    outputMedia: r.outputMedia
                })));
            }
        } catch (error) {
            console.error("Failed to fetch radars", error);
        }
    }, [user]);

    // Fetch items for a specific radar
    const fetchRadarItems = useCallback(async (radarId: string) => {
        if (!user) return;
        setLoadingItems(true);
        try {
            const token = await user.getIdToken();
            const res = await fetch(`/api/radars/${radarId}/items`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setItems(data);
            }
        } catch (error) {
            console.error("Error fetching radar items:", error);
        } finally {
            setLoadingItems(false);
        }
    }, [user]);

    // Sync radar (trigger + poll)
    const syncRadar = async (radarId: string, initialCount: number, onUpdate: (msg: string) => void) => {
        if (!user) return;
        setLoadingItems(true);
        try {
            const token = await user.getIdToken();
            // 1. Trigger sync
            const syncRes = await fetch(`/api/radars/${radarId}/sync`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (syncRes.ok) {
                // 2. Poll for results
                let attempts = 0;
                const maxAttempts = 12;
                let foundNew = false;

                while (attempts < maxAttempts) {
                    attempts++;
                    await new Promise(resolve => setTimeout(resolve, 10000)); // 10s wait

                    try {
                        const itemsRes = await fetch(`/api/radars/${radarId}/items`, {
                            headers: { 'Authorization': `Bearer ${token}` }
                        });
                        if (itemsRes.ok) {
                            const newItems = await itemsRes.json();
                            if (newItems.length > initialCount) {
                                setItems(newItems);
                                onUpdate(`**Sync Complete.** Found ${newItems.length - initialCount} new items.`);
                                foundNew = true;
                                break;
                            }
                        }
                    } catch (e) {
                        console.error("Polling error", e);
                    }
                }
                if (!foundNew) {
                    onUpdate("Sync timed out or no new items were found.");
                }
            } else {
                onUpdate(`Error syncing radar: ${syncRes.statusText}`);
            }

        } catch (error) {
            console.error("Error syncing radar", error);
            onUpdate(`Error syncing radar: ${error}`);
        } finally {
            setLoadingItems(false);
        }
    };

    const deleteItem = async (radarId: string, itemId: string) => {
        if (!user) return;
        try {
            const token = await user.getIdToken();
            const res = await fetch(`/api/radars/${radarId}/items/${itemId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                setItems(prev => prev.filter(i => i.id !== itemId));
            }
        } catch (error) {
            console.error("Error deleting radar item", error);
        }
    };

    return {
        radars,
        items,
        loadingItems,
        fetchRadars,
        fetchRadarItems,
        syncRadar,
        deleteItem,
        setItems // Expose raw setter if needed
    };
};
