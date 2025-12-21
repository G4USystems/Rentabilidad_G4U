import { useState, useMemo } from 'react';
import { formatCurrency, formatDate, isIncome } from '../utils/format';
import { api } from '../hooks/useApi';

export default function Review({ transactions, projects, clients, onRefresh, showToast }) {
  const [selectedTx, setSelectedTx] = useState(null);
  const [allocations, setAllocations] = useState([{ project: '', client: '', percentage: 100 }]);
  const [sortBy, setSortBy] = useState('date-desc');
  const [saving, setSaving] = useState(false);

  // Pending transactions
  const pending = useMemo(() => {
    let items = transactions.filter(t =>
      !t.project && !t.project_id && !t.client && !t.client_id && !t.excluded
    );

    items.sort((a, b) => {
      switch (sortBy) {
        case 'date-asc':
          return new Date(a.settled_at) - new Date(b.settled_at);
        case 'amount-desc':
          return Math.abs(parseFloat(b.amount)) - Math.abs(parseFloat(a.amount));
        case 'amount-asc':
          return Math.abs(parseFloat(a.amount)) - Math.abs(parseFloat(b.amount));
        default:
          return new Date(b.settled_at) - new Date(a.settled_at);
      }
    });

    return items;
  }, [transactions, sortBy]);

  const totalPercentage = allocations.reduce((sum, a) => sum + (parseInt(a.percentage) || 0), 0);
  const isValid = totalPercentage === 100 && allocations.some(a => a.project || a.client);

  const selectTransaction = (tx) => {
    setSelectedTx(tx);
    setAllocations([{ project: '', client: '', percentage: 100 }]);
  };

  const updateAllocation = (index, field, value) => {
    setAllocations(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const addAllocation = () => {
    setAllocations(prev => [...prev, { project: '', client: '', percentage: 0 }]);
  };

  const removeAllocation = (index) => {
    if (allocations.length > 1) {
      setAllocations(prev => prev.filter((_, i) => i !== index));
    }
  };

  const saveAssignment = async () => {
    if (!selectedTx || !isValid) return;

    setSaving(true);
    try {
      const validAllocations = allocations.filter(a => a.project || a.client);

      if (validAllocations.length === 1 && validAllocations[0].percentage === 100) {
        await api.updateTransaction(selectedTx.id, {
          project_id: validAllocations[0].project || null,
          client_id: validAllocations[0].client || null
        });
      } else {
        await api.createAllocation({
          transaction_id: selectedTx.id,
          allocations: validAllocations.map(a => ({
            project_id: a.project || null,
            client_id: a.client || null,
            percentage: parseInt(a.percentage)
          }))
        });
      }

      showToast('Transaccion asignada correctamente', 'success');
      setSelectedTx(null);
      setAllocations([{ project: '', client: '', percentage: 100 }]);
      onRefresh();
    } catch (error) {
      showToast('Error al guardar: ' + error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const excludeTransaction = async () => {
    if (!selectedTx) return;

    setSaving(true);
    try {
      await api.updateTransaction(selectedTx.id, { excluded: true });
      showToast('Transaccion excluida', 'success');
      setSelectedTx(null);
      onRefresh();
    } catch (error) {
      showToast('Error: ' + error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const amount = selectedTx ? parseFloat(selectedTx.amount) || 0 : 0;
  const income = selectedTx ? isIncome(selectedTx) : false;

  return (
    <div className="animate-fadeIn grid grid-cols-5 gap-6 h-[calc(100vh-160px)]">
      {/* Pending List */}
      <div className="col-span-3 bg-white border border-slate-200 rounded-xl flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <span className="font-semibold text-slate-900">{pending.length} pendientes</span>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="text-sm border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="date-desc">Mas recientes</option>
            <option value="date-asc">Mas antiguas</option>
            <option value="amount-desc">Mayor monto</option>
            <option value="amount-asc">Menor monto</option>
          </select>
        </div>

        <div className="flex-1 overflow-y-auto">
          {pending.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400">
              <CheckIcon className="w-16 h-16 mb-4 opacity-30" />
              <p className="font-medium">Todas las transacciones estan asignadas</p>
            </div>
          ) : (
            pending.map(tx => {
              const txAmount = parseFloat(tx.amount) || 0;
              const txIncome = isIncome(tx);
              const isSelected = selectedTx?.id === tx.id;

              return (
                <div
                  key={tx.id}
                  onClick={() => selectTransaction(tx)}
                  className={`flex items-center gap-4 px-5 py-4 border-b border-slate-100 cursor-pointer transition-colors ${
                    isSelected ? 'bg-blue-50 border-l-4 border-l-blue-600' : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-900 truncate">
                      {tx.counterparty_name || tx.label || 'Sin descripcion'}
                    </p>
                    <p className="text-sm text-slate-500">
                      {formatDate(tx.settled_at || tx.emitted_at)} · {tx.qonto_category || '-'}
                    </p>
                  </div>
                  <span className={`font-mono font-semibold ${txIncome ? 'text-emerald-600' : 'text-red-500'}`}>
                    {txIncome ? '+' : ''}{formatCurrency(txAmount)}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Assignment Panel */}
      <div className="col-span-2 bg-white border border-slate-200 rounded-xl flex flex-col overflow-hidden">
        {!selectedTx ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
            <ClipboardIcon className="w-16 h-16 mb-4 opacity-30" />
            <p className="font-medium">Selecciona una transaccion</p>
            <p className="text-sm">para asignar proyecto o cliente</p>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="p-5 border-b border-slate-200">
              <div className="bg-slate-50 rounded-lg p-4">
                <p className="font-semibold text-slate-900 mb-1">
                  {selectedTx.counterparty_name || selectedTx.label || 'Transaccion'}
                </p>
                <p className={`text-2xl font-bold font-mono ${income ? 'text-emerald-600' : 'text-red-500'}`}>
                  {income ? '+' : ''}{formatCurrency(amount)}
                </p>
                <p className="text-sm text-slate-500 mt-2">
                  {formatDate(selectedTx.settled_at || selectedTx.emitted_at)} · {selectedTx.qonto_category || '-'}
                </p>
              </div>
            </div>

            {/* Allocations */}
            <div className="flex-1 p-5 overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-semibold text-slate-900">Asignaciones</h4>
                <button
                  onClick={addAllocation}
                  className="text-sm text-blue-600 font-medium hover:underline"
                >
                  + Agregar
                </button>
              </div>

              <div className="space-y-3">
                {allocations.map((alloc, index) => (
                  <div key={index} className="grid grid-cols-12 gap-2 p-3 bg-slate-50 rounded-lg items-center">
                    <select
                      value={alloc.project}
                      onChange={e => updateAllocation(index, 'project', e.target.value)}
                      className="col-span-4 px-2 py-2 border border-slate-200 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Proyecto...</option>
                      {projects.map(p => (
                        <option key={p.id || p.name} value={p.id || p.name}>{p.name}</option>
                      ))}
                    </select>

                    <select
                      value={alloc.client}
                      onChange={e => updateAllocation(index, 'client', e.target.value)}
                      className="col-span-4 px-2 py-2 border border-slate-200 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Cliente...</option>
                      {clients.map(c => (
                        <option key={c.id || c.name} value={c.id || c.name}>{c.name}</option>
                      ))}
                    </select>

                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={alloc.percentage}
                      onChange={e => updateAllocation(index, 'percentage', e.target.value)}
                      className="col-span-3 px-2 py-2 border border-slate-200 rounded text-sm text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />

                    <button
                      onClick={() => removeAllocation(index)}
                      disabled={allocations.length === 1}
                      className="col-span-1 p-2 text-slate-400 hover:text-red-500 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <XIcon className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>

              <div className={`mt-4 p-3 rounded-lg flex justify-between font-semibold ${
                totalPercentage === 100 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
              }`}>
                <span>Total asignado:</span>
                <span>{totalPercentage}%</span>
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-between">
              <button
                onClick={excludeTransaction}
                disabled={saving}
                className="px-4 py-2 text-red-600 font-medium hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
              >
                Excluir
              </button>
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedTx(null)}
                  className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={saveAssignment}
                  disabled={!isValid || saving}
                  className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function CheckIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
    </svg>
  );
}

function ClipboardIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
      <rect x="9" y="3" width="6" height="4" rx="1"/>
      <path d="M9 14l2 2 4-4"/>
    </svg>
  );
}

function XIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M6 18L18 6M6 6l12 12"/>
    </svg>
  );
}
