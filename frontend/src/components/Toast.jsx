import { useEffect } from 'react';

export default function Toast({ toasts, onRemove }) {
  return (
    <div className="fixed top-20 right-6 flex flex-col gap-2 z-50">
      {toasts.map(toast => (
        <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onRemove }) {
  useEffect(() => {
    const timer = setTimeout(() => onRemove(toast.id), 5000);
    return () => clearTimeout(timer);
  }, [toast.id, onRemove]);

  const borderColors = {
    success: 'border-l-emerald-500',
    error: 'border-l-red-500',
    warning: 'border-l-amber-500',
    info: 'border-l-blue-500',
  };

  return (
    <div
      className={`flex items-center gap-4 px-4 py-3 bg-white border border-slate-200 border-l-4 ${borderColors[toast.type]} rounded-lg shadow-lg animate-slideIn max-w-sm`}
      style={{ animation: 'slideIn 0.3s ease-out' }}
    >
      <span className="flex-1 text-sm text-slate-700">{toast.message}</span>
      <button
        onClick={() => onRemove(toast.id)}
        className="text-slate-400 hover:text-slate-600 text-lg"
      >
        &times;
      </button>
    </div>
  );
}
