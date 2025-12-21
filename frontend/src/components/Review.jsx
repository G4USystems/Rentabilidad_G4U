import { useState, useMemo, useEffect } from 'react';
import { formatCurrency, formatDate, isIncome } from '../utils/format';
import { api } from '../hooks/useApi';

export default function Review({ transactions, projects, clients, onRefresh, showToast }) {
  const [animate, setAnimate] = useState(false);
  const [selectedTx, setSelectedTx] = useState(null);
  const [allocations, setAllocations] = useState([{ project: '', client: '', percentage: 100 }]);
  const [sortBy, setSortBy] = useState('date-desc');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setAnimate(true);
  }, []);

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

  // Calculate totals
  const totals = useMemo(() => {
    const income = pending.filter(t => isIncome(t)).reduce((s, t) => s + Math.abs(parseFloat(t.amount) || 0), 0);
    const expenses = pending.filter(t => !isIncome(t)).reduce((s, t) => s + Math.abs(parseFloat(t.amount) || 0), 0);
    return { income, expenses, total: income + expenses };
  }, [pending]);

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
    <div className="space-y-6">
      {/* Header Stats */}
      <div
        className={`grid grid-cols-3 gap-4 transition-all duration-500 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
      >
        <div
          className="bg-gradient-to-br from-amber-500 to-orange-600 rounded-2xl p-6 text-white"
          style={{ boxShadow: '0 8px 32px -8px rgba(245,158,11,0.4)' }}
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-white/20 backdrop-blur rounded-xl flex items-center justify-center">
              <span className="text-xl">⏳</span>
            </div>
            <span className="text-white/80 font-medium">Pendientes</span>
          </div>
          <p className="text-4xl font-bold">{pending.length}</p>
          <p className="text-white/70 text-sm mt-1">transacciones sin asignar</p>
        </div>

        <div
          className="bg-white rounded-2xl border border-slate-200 p-6"
          style={{ boxShadow: '0 4px 24px -4px rgba(0,0,0,0.06)' }}
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center">
              <span className="text-emerald-600 text-xl">↑</span>
            </div>
            <span className="text-slate-600 font-medium">Ingresos pendientes</span>
          </div>
          <p className="text-2xl font-bold text-emerald-600 font-mono">{formatCurrency(totals.income, true)}</p>
        </div>

        <div
          className="bg-white rounded-2xl border border-slate-200 p-6"
          style={{ boxShadow: '0 4px 24px -4px rgba(0,0,0,0.06)' }}
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-red-100 rounded-xl flex items-center justify-center">
              <span className="text-red-600 text-xl">↓</span>
            </div>
            <span className="text-slate-600 font-medium">Gastos pendientes</span>
          </div>
          <p className="text-2xl font-bold text-red-600 font-mono">{formatCurrency(totals.expenses, true)}</p>
        </div>
      </div>

      {/* Main Content */}
      <div
        className={`grid grid-cols-5 gap-6 transition-all duration-500 delay-100 ${animate ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
        style={{ minHeight: 'calc(100vh - 320px)' }}
      >
        {/* Pending List */}
        <div
          className="col-span-3 bg-white border border-slate-200 rounded-2xl flex flex-col overflow-hidden"
          style={{ boxShadow: '0 4px 24px -4px rgba(0,0,0,0.06)' }}
        >
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <h3 className="font-semibold text-slate-900">Cola de revision</h3>
              <span className="px-2.5 py-1 bg-amber-100 text-amber-700 text-sm font-medium rounded-full">
                {pending.length}
              </span>
            </div>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              className="text-sm border border-slate-200 rounded-xl px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            >
              <option value="date-desc">Mas recientes</option>
              <option value="date-asc">Mas antiguas</option>
              <option value="amount-desc">Mayor monto</option>
              <option value="amount-asc">Menor monto</option>
            </select>
          </div>

          <div className="flex-1 overflow-y-auto">
            {pending.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full py-16">
                <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mb-4">
                  <CheckIcon className="w-10 h-10 text-emerald-600" />
                </div>
                <p className="font-semibold text-slate-900 text-lg">Todo asignado</p>
                <p className="text-slate-500 mt-1">No hay transacciones pendientes</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {pending.map((tx, i) => {
                  const txAmount = parseFloat(tx.amount) || 0;
                  const txIncome = isIncome(tx);
                  const isSelected = selectedTx?.id === tx.id;

                  return (
                    <div
                      key={tx.id}
                      onClick={() => selectTransaction(tx)}
                      className={`flex items-center gap-4 px-6 py-4 cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-blue-50 border-l-4 border-l-blue-600'
                          : 'hover:bg-slate-50 border-l-4 border-l-transparent'
                      }`}
                    >
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                        txIncome ? 'bg-emerald-100 text-emerald-600' : 'bg-red-100 text-red-600'
                      }`}>
                        {txIncome ? '↑' : '↓'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-900 truncate">
                          {tx.counterparty_name || tx.label || 'Sin descripcion'}
                        </p>
                        <p className="text-sm text-slate-500 flex items-center gap-2">
                          <span>{formatDate(tx.settled_at || tx.emitted_at)}</span>
                          <span className="w-1 h-1 bg-slate-300 rounded-full" />
                          <span>{tx.qonto_category || '-'}</span>
                        </p>
                      </div>
                      <span className={`font-mono font-bold text-lg ${txIncome ? 'text-emerald-600' : 'text-red-500'}`}>
                        {txIncome ? '+' : ''}{formatCurrency(txAmount, true)}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Assignment Panel */}
        <div
          className="col-span-2 bg-white border border-slate-200 rounded-2xl flex flex-col overflow-hidden"
          style={{ boxShadow: '0 4px 24px -4px rgba(0,0,0,0.06)' }}
        >
          {!selectedTx ? (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400 p-8">
              <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                <ClipboardIcon className="w-10 h-10" />
              </div>
              <p className="font-semibold text-slate-700 text-lg">Selecciona una transaccion</p>
              <p className="text-slate-500 text-center mt-1">
                Haz clic en una transaccion de la lista para asignarla a un proyecto o cliente
              </p>
            </div>
          ) : (
            <>
              {/* Header */}
              <div className="p-6 border-b border-slate-100">
                <div className={`rounded-xl p-5 ${income ? 'bg-emerald-50' : 'bg-red-50'}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-slate-900 truncate">
                        {selectedTx.counterparty_name || selectedTx.label || 'Transaccion'}
                      </p>
                      <p className="text-sm text-slate-500 mt-1">
                        {formatDate(selectedTx.settled_at || selectedTx.emitted_at)} · {selectedTx.qonto_category || '-'}
                      </p>
                    </div>
                    <p className={`text-3xl font-bold font-mono flex-shrink-0 ${income ? 'text-emerald-600' : 'text-red-600'}`}>
                      {income ? '+' : ''}{formatCurrency(amount)}
                    </p>
                  </div>
                </div>
              </div>

              {/* Allocations */}
              <div className="flex-1 p-6 overflow-y-auto">
                <div className="flex items-center justify-between mb-5">
                  <h4 className="font-semibold text-slate-900">Asignaciones</h4>
                  <button
                    onClick={addAllocation}
                    className="px-4 py-2 text-sm text-blue-600 font-medium bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
                  >
                    + Dividir
                  </button>
                </div>

                <div className="space-y-4">
                  {allocations.map((alloc, index) => (
                    <div
                      key={index}
                      className="p-4 bg-slate-50 rounded-xl border border-slate-200"
                    >
                      <div className="grid grid-cols-2 gap-3 mb-3">
                        <div>
                          <label className="block text-xs font-medium text-slate-500 mb-1.5">Proyecto</label>
                          <select
                            value={alloc.project}
                            onChange={e => updateAllocation(index, 'project', e.target.value)}
                            className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            <option value="">Sin proyecto</option>
                            {projects.map(p => (
                              <option key={p.id || p.name} value={p.id || p.name}>{p.name}</option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-500 mb-1.5">Cliente</label>
                          <select
                            value={alloc.client}
                            onChange={e => updateAllocation(index, 'client', e.target.value)}
                            className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            <option value="">Sin cliente</option>
                            {clients.map(c => (
                              <option key={c.id || c.name} value={c.id || c.name}>{c.name}</option>
                            ))}
                          </select>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <div className="flex-1">
                          <div className="flex items-center justify-between text-xs font-medium text-slate-500 mb-1.5">
                            <span>Porcentaje</span>
                            <span className="text-slate-700">{alloc.percentage}%</span>
                          </div>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={alloc.percentage}
                            onChange={e => updateAllocation(index, 'percentage', e.target.value)}
                            className="w-full h-2 bg-slate-200 rounded-full appearance-none cursor-pointer accent-blue-600"
                          />
                        </div>
                        {allocations.length > 1 && (
                          <button
                            onClick={() => removeAllocation(index)}
                            className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <XIcon className="w-5 h-5" />
                          </button>
                        )}
                      </div>

                      {alloc.percentage > 0 && (
                        <p className="text-sm text-slate-500 mt-3 pt-3 border-t border-slate-200 font-mono">
                          = {formatCurrency(Math.abs(amount) * (alloc.percentage / 100))}
                        </p>
                      )}
                    </div>
                  ))}
                </div>

                {/* Total Bar */}
                <div className={`mt-5 p-4 rounded-xl flex items-center justify-between font-semibold ${
                  totalPercentage === 100
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-red-50 text-red-700 border border-red-200'
                }`}>
                  <span>Total asignado</span>
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-2 bg-white/50 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${totalPercentage === 100 ? 'bg-emerald-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.min(100, totalPercentage)}%` }}
                      />
                    </div>
                    <span>{totalPercentage}%</span>
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-between">
                <button
                  onClick={excludeTransaction}
                  disabled={saving}
                  className="px-5 py-2.5 text-red-600 font-medium hover:bg-red-50 rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  <XIcon className="w-4 h-4" />
                  Excluir
                </button>
                <div className="flex gap-2">
                  <button
                    onClick={() => setSelectedTx(null)}
                    className="px-5 py-2.5 text-slate-600 font-medium hover:bg-slate-100 rounded-xl transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={saveAssignment}
                    disabled={!isValid || saving}
                    className="px-6 py-2.5 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {saving ? (
                      <>
                        <LoadingSpinner />
                        Guardando...
                      </>
                    ) : (
                      <>
                        <CheckIcon className="w-4 h-4" />
                        Guardar
                      </>
                    )}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

function CheckIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 6L9 17l-5-5"/>
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
