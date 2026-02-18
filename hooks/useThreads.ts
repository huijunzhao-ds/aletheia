import { useState, useCallback } from 'react';
import { User } from 'firebase/auth';

export interface Thread {
    id: string;
    title: string;
    radarId?: string;
    // Add other properties if needed
}

export const useThreads = (user: User | null) => {
    const [threads, setThreads] = useState<Thread[]>([]);
    const [loading, setLoading] = useState(false);

    const fetchThreads = useCallback(async (agentType: string = 'exploration', radarId?: string) => {
        if (!user) return [];
        setLoading(true);
        try {
            const token = await user.getIdToken();
            let url = `/api/threads?agent_type=${agentType}`;
            if (radarId) {
                url += `&radar_id=${radarId}`;
            }

            const res = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!res.ok) throw new Error('Failed to fetch threads');

            const data = await res.json();
            return data.threads || [];
        } catch (e) {
            console.error("Error refreshing threads", e);
            return [];
        } finally {
            setLoading(false);
        }
    }, [user]);

    const replaceThreads = (newThreads: Thread[]) => {
        setThreads(newThreads);
    };

    const mergeThreads = (newThreads: Thread[]) => {
        setThreads(prev => {
            const existingIds = new Set(prev.map(t => t.id));
            const uniqueNewThreads = newThreads.filter(t => !existingIds.has(t.id));
            return [...uniqueNewThreads, ...prev];
        });
    };

    const addThread = (thread: Thread) => {
        setThreads(prev => [thread, ...prev]);
    };

    const deleteThread = async (threadId: string, agentType: string) => {
        if (!user) return false;
        try {
            const token = await user.getIdToken();
            const response = await fetch(`/api/threads/${threadId}?agent_type=${agentType}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                setThreads(prev => prev.filter(t => t.id !== threadId));
                return true;
            }
            return false;
        } catch (error) {
            console.error("Error deleting thread:", error);
            return false;
        }
    };

    return {
        threads,
        loading,
        fetchThreads,
        replaceThreads,
        mergeThreads,
        addThread,
        deleteThread,
        setThreads // Expose raw setter if needed for rare cases
    };
};
