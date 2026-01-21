import React from 'react';

interface DocumentViewerProps {
    url: string;
    name: string;
    onClose: () => void;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({ url, name, onClose }) => {
    return (
        <div className="flex flex-col h-full bg-zinc-900 border-l border-zinc-800 animate-in slide-in-from-right duration-500">
            <div className="flex items-center justify-between px-4 py-3 bg-zinc-950 border-b border-zinc-800">
                <div className="flex items-center space-x-3">
                    <div className="p-1.5 bg-red-500/20 rounded">
                        <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                        </svg>
                    </div>
                    <span className="text-zinc-200 text-sm font-semibold truncate max-w-[200px]">{name}</span>
                </div>
                <button
                    onClick={onClose}
                    className="p-1.5 text-zinc-500 hover:text-white hover:bg-zinc-800 rounded transition-all"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
            <div className="flex-1 bg-zinc-800 relative">
                <iframe
                    src={`${url}#toolbar=0&navpanes=0&scrollbar=0`}
                    className="w-full h-full border-none"
                    title={name}
                />
            </div>
        </div>
    );
};
