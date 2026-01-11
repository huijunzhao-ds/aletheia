import React from 'react';

interface DocumentViewerProps {
    url: string;
    name: string;
    onClose: () => void;
    unavailable?: boolean;
    onReupload?: () => void;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({ url, name, onClose, unavailable, onReupload }) => {
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

            <div className="flex-1 bg-zinc-800 relative flex flex-col items-center justify-center p-8 text-center">
                {unavailable ? (
                    <div className="max-w-md space-y-6 animate-in fade-in zoom-in duration-500">
                        <div className="w-20 h-20 bg-zinc-900 rounded-2xl flex items-center justify-center mx-auto shadow-2xl border border-zinc-700">
                            <svg className="w-10 h-10 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                        </div>
                        <div className="space-y-2">
                            <h3 className="text-xl font-bold text-zinc-200">File Unavailable</h3>
                            <p className="text-zinc-400 text-sm leading-relaxed">
                                This document was uploaded in a different environment (like your local development machine) and is not synced to this cloud instance.
                            </p>
                        </div>
                        <div className="pt-4 flex flex-col gap-3">
                            <button
                                onClick={onReupload}
                                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition-all shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-2"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                                </svg>
                                Restore & Re-upload
                            </button>
                            <button
                                onClick={onClose}
                                className="px-6 py-2 text-zinc-500 hover:text-zinc-300 rounded-lg text-sm font-medium transition-colors"
                            >
                                Go Back to Chat
                            </button>
                        </div>
                    </div>
                ) : (
                    <iframe
                        src={`${url}#toolbar=0&navpanes=0&scrollbar=0`}
                        className="w-full h-full border-none"
                        title={name}
                    />
                )}
            </div>
        </div>
    );
};
