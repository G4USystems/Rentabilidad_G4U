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
        case 'date-asc': return new Date(a.settled_at) - new Date(b.settled_at);
        case 'amount-desc': return Math.abs(parseFloat(b.amount)) - Math.abs(parseFloat(a.amount));
        case 'amount-asc': return Math.abs(parseFloat(a.amount)) - Math.abs(parseFloat(b.amount));
        default: return new Date(b.settled_at) - new Date(a.settled_at);
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
      showToast('Transaccion asignada', 'success');
      setSelectedTx(null);
      setAllocations([{ project: '', client: '', percentage: 100 }]);
      onRefresh();
    } catch (error) {
      showToast('Error: ' + error.message, 'error');
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
    <div className="flex gap-6" style={{ height: 'calc(100vh - 180px)' }}>
      {/* Left: Pending List */}
      <div className="flex-1 bg-white rounded-lg border border-slate-200 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
          <span className="font-semibold">{pending.length} pendientes</span>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="text-sm border rounded px-2 py-1"
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
              <span className="text-4xl mb-2">✓</span>
              <p>Todo asignado</p>
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
                  className={`flex items-center gap-3 px-4 py-3 border-b border-slate-100 cursor-pointer ${
                    isSelected ? 'bg-blue-50 border-l-4 border-l-blue-500' : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{tx.counterparty_name || tx.label || 'Sin descripcion'}</p>
                    <p className="text-sm text-slate-500">{formatDate(tx.settled_at)} · {tx.qonto_category || '-'}</p>
                  </div>
                  <span className={`font-mono font-semibold ${txIncome ? 'text-emerald-600' : 'text-red-500'}`}>
                    {txIncome ? '+' : ''}{formatCurrency(txAmount, true)}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right: Assignment Panel */}
      <div className="w-96 bg-white rounded-lg border border-slate-200 flex flex-col overflow-hidden">
        {!selectedTx ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
            <span className="text-4xl mb-2">📋</span>
            <p>Selecciona una transaccion</p>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="p-4 border-b border-slate-200">
              <p className="font-medium truncate">{selectedTx.counterparty_name || selectedTx.label}</p>
              <p className={`text-2xl font-bold font-mono ${income ? 'text-emerald-600' : 'text-red-500'}`}>
                {income ? '+' : ''}{formatCurrency(amount)}
              </p>
              <p className="text-sm text-slate-500 mt-1">
                {formatDate(selectedTx.settled_at)} · {selectedTx.qonto_category || '-'}
              </p>
            </div>

            {/* Allocations */}
            <div className="flex-1 p-4 overflow-y-auto">
              <div className="flex items-center justify-between mb-3">
                <span className="font-semibold">Asignaciones</span>
                <button onClick={addAllocation} className="text-sm text-blue-600">+ Agregar</button>
              </div>

              <div className="space-y-3">
                {allocations.map((alloc, i) => (
                  <div key={i} className="p-3 bg-slate-50 rounded-lg">
                    <div className="grid grid-cols-2 gap-2 mb-2">
                      <select
                        value={alloc.project}
                        onChange={e => updateAllocation(i, 'project', e.target.value)}
                        className="px-2 py-1.5 border rounded text-sm"
                      >
                        <option value="">Proyecto...</option>
                        {projects.map(p => (
                          <option key={p.id || p.name} value={p.id || p.name}>{p.name}</option>
                        ))}
                      </select>
                      <select
                        value={alloc.client}
                        onChange={e => updateAllocation(i, 'client', e.target.value)}
                        className="px-2 py-1.5 border rounded text-sm"
                      >
                        <option value="">Cliente...</option>
                        {clients.map(c => (
                          <option key={c.id || c.name} value={c.id || c.name}>{c.name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={alloc.percentage}
                        onChange={e => updateAllocation(i, 'percentage', e.target.value)}
                        className="w-20 px-2 py-1 border rounded text-sm text-center"
                      />
                      <span className="text-sm text-slate-500">%</span>
                      {allocations.length > 1 && (
                        <button onClick={() => removeAllocation(i)} className="ml-auto text-red-500 text-sm">✕</button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className={`mt-4 p-3 rounded-lg text-center font-semibold ${
                totalPercentage === 100 ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
              }`}>
                Total: {totalPercentage}%
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-slate-200 flex justify-between">
              <button
                onClick={excludeTransaction}
                disabled={saving}
                className="px-3 py-2 text-red-600 text-sm font-medium"
              >
                Excluir
              </button>
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedTx(null)}
                  className="px-3 py-2 text-slate-600 text-sm"
                >
                  Cancelar
                </button>
                <button
                  onClick={saveAssignment}
                  disabled={!isValid || saving}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded disabled:opacity-50"
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
