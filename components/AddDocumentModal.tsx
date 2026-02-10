import React, { useState } from 'react';

interface AddDocumentModalProps {
    isOpen: boolean;
    onClose: () => void;
    onAdd: (mode: 'url' | 'upload', title: string, url: string, file: File | null) => Promise<boolean>;
}

export const AddDocumentModal: React.FC<AddDocumentModalProps> = ({ isOpen, onClose, onAdd }) => {
    const [mode, setMode] = useState<'url' | 'upload'>('url');
    const [title, setTitle] = useState('');
    const [url, setUrl] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const [isAdding, setIsAdding] = useState(false);

    if (!isOpen) return null;

    const handleSubmit = async () => {
        setIsAdding(true);
        const success = await onAdd(mode, title, url, file);
        setIsAdding(false);
        if (success) {
            // Reset form
            setMode('url');
            setTitle('');
            setUrl('');
            setFile(null);
            onClose();
        }
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 w-[400px] space-y-4 shadow-xl">
                <h3 className="text-lg font-medium text-white">Add to Exploration</h3>

                <div className="flex space-x-4 border-b border-zinc-800 pb-2">
                    <button
                        className={`pb-1 px-1 ${mode === 'url' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-zinc-400'}`}
                        onClick={() => setMode('url')}
                    >
                        From URL
                    </button>
                    <button
                        className={`pb-1 px-1 ${mode === 'upload' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-zinc-400'}`}
                        onClick={() => setMode('upload')}
                    >
                        Upload File
                    </button>
                </div>

                <div className="space-y-3">
                    <div>
                        <label className="block text-xs text-zinc-400 mb-1">Title (Optional)</label>
                        <input
                            type="text"
                            value={title}
                            onChange={e => setTitle(e.target.value)}
                            className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                            placeholder="Article Title"
                        />
                    </div>

                    {mode === 'url' ? (
                        <div>
                            <label className="block text-xs text-zinc-400 mb-1">URL</label>
                            <input
                                type="text"
                                value={url}
                                onChange={e => setUrl(e.target.value)}
                                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                                placeholder="https://arxiv.org/pdf/..."
                            />
                        </div>
                    ) : (
                        <div>
                            <label className="block text-xs text-zinc-400 mb-1">File</label>
                            <input
                                type="file"
                                onChange={e => setFile(e.target.files ? e.target.files[0] : null)}
                                className="w-full text-sm text-zinc-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-500/10 file:text-blue-400 hover:file:bg-blue-500/20"
                            />
                        </div>
                    )}
                </div>

                <div className="flex justify-end space-x-2 pt-2">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm text-zinc-400 hover:text-white"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={isAdding || (mode === 'url' ? !url : !file)}
                        className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isAdding ? 'Adding...' : 'Add Resource'}
                    </button>
                </div>
            </div>
        </div>
    );
};
