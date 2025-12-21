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
      showToast('Transacción asignada correctamente', 'success');
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
      showToast('Transacción excluida', 'success');
      setSelectedTx(null);
      onRefresh();
    } catch (error) {
      showToast('Error: ' + error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const amount = selectedTx ? Math.abs(parseFloat(selectedTx.amount) || 0) : 0;
  const income = selectedTx ? isIncome(selectedTx) : false;

  // Styles
  const cardStyle = {
    backgroundColor: 'white',
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
    overflow: 'hidden'
  };

  return (
    <div style={{ display: 'flex', gap: '24px', height: 'calc(100vh - 180px)' }}>
      {/* Left Panel - Pending List */}
      <div style={{ flex: '1', display: 'flex', flexDirection: 'column', ...cardStyle }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          borderBottom: '1px solid #f1f5f9'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontWeight: '600', fontSize: '16px', color: '#1e293b' }}>
              Pendientes
            </span>
            <span style={{
              padding: '4px 10px',
              backgroundColor: '#fef3c7',
              color: '#d97706',
              borderRadius: '20px',
              fontSize: '13px',
              fontWeight: '600'
            }}>
              {pending.length}
            </span>
          </div>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            style={{
              padding: '6px 12px',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              fontSize: '13px',
              backgroundColor: 'white'
            }}
          >
            <option value="date-desc">Más recientes</option>
            <option value="date-asc">Más antiguas</option>
            <option value="amount-desc">Mayor monto</option>
            <option value="amount-asc">Menor monto</option>
          </select>
        </div>

        {/* List */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {pending.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#94a3b8' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>✓</div>
              <div style={{ fontWeight: '500', fontSize: '16px' }}>Todo asignado</div>
              <div style={{ fontSize: '14px', marginTop: '4px' }}>No hay transacciones pendientes</div>
            </div>
          ) : (
            pending.map(tx => {
              const txAmount = Math.abs(parseFloat(tx.amount) || 0);
              const txIncome = isIncome(tx);
              const isSelected = selectedTx?.id === tx.id;

              return (
                <div
                  key={tx.id}
                  onClick={() => selectTransaction(tx)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '16px 20px',
                    borderBottom: '1px solid #f1f5f9',
                    cursor: 'pointer',
                    backgroundColor: isSelected ? '#eff6ff' : 'white',
                    borderLeft: isSelected ? '4px solid #3b82f6' : '4px solid transparent',
                    transition: 'all 0.15s'
                  }}
                >
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '10px',
                    backgroundColor: txIncome ? '#ecfdf5' : '#fef2f2',
                    color: txIncome ? '#10b981' : '#ef4444',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: '600',
                    flexShrink: 0
                  }}>
                    {txIncome ? '↑' : '↓'}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: '500', color: '#1e293b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {tx.counterparty_name || tx.label || 'Sin descripción'}
                    </div>
                    <div style={{ fontSize: '13px', color: '#64748b', marginTop: '2px' }}>
                      {formatDate(tx.settled_at || tx.emitted_at)} · {tx.qonto_category || '-'}
                    </div>
                  </div>
                  <div style={{
                    fontFamily: 'monospace',
                    fontWeight: '600',
                    fontSize: '15px',
                    color: txIncome ? '#10b981' : '#ef4444'
                  }}>
                    {txIncome ? '+' : '-'}{formatCurrency(txAmount, true)}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Panel - Assignment Form */}
      <div style={{ width: '400px', display: 'flex', flexDirection: 'column', ...cardStyle }}>
        {!selectedTx ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#94a3b8', padding: '40px' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
            <div style={{ fontWeight: '500', fontSize: '16px', color: '#64748b' }}>Selecciona una transacción</div>
            <div style={{ fontSize: '14px', marginTop: '8px', textAlign: 'center' }}>
              Haz clic en una transacción para asignarla a un proyecto o cliente
            </div>
          </div>
        ) : (
          <>
            {/* Selected Transaction Header */}
            <div style={{ padding: '20px', borderBottom: '1px solid #f1f5f9' }}>
              <div style={{
                padding: '16px',
                borderRadius: '10px',
                backgroundColor: income ? '#ecfdf5' : '#fef2f2'
              }}>
                <div style={{ fontWeight: '500', color: '#1e293b', marginBottom: '8px' }}>
                  {selectedTx.counterparty_name || selectedTx.label || 'Transacción'}
                </div>
                <div style={{
                  fontSize: '28px',
                  fontWeight: '700',
                  fontFamily: 'monospace',
                  color: income ? '#10b981' : '#ef4444'
                }}>
                  {income ? '+' : '-'}{formatCurrency(amount)}
                </div>
                <div style={{ fontSize: '13px', color: '#64748b', marginTop: '8px' }}>
                  {formatDate(selectedTx.settled_at || selectedTx.emitted_at)} · {selectedTx.qonto_category || '-'}
                </div>
              </div>
            </div>

            {/* Allocation Form */}
            <div style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <span style={{ fontWeight: '600', color: '#1e293b' }}>Asignaciones</span>
                <button
                  onClick={addAllocation}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: '#eff6ff',
                    color: '#3b82f6',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '13px',
                    fontWeight: '500',
                    cursor: 'pointer'
                  }}
                >
                  + Dividir
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {allocations.map((alloc, i) => (
                  <div key={i} style={{ padding: '16px', backgroundColor: '#f8fafc', borderRadius: '10px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
                      <div>
                        <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '4px' }}>Proyecto</label>
                        <select
                          value={alloc.project}
                          onChange={e => updateAllocation(i, 'project', e.target.value)}
                          style={formSelectStyle}
                        >
                          <option value="">Sin proyecto</option>
                          {projects.map(p => (
                            <option key={p.id || p.name} value={p.id || p.name}>{p.name}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '4px' }}>Cliente</label>
                        <select
                          value={alloc.client}
                          onChange={e => updateAllocation(i, 'client', e.target.value)}
                          style={formSelectStyle}
                        >
                          <option value="">Sin cliente</option>
                          {clients.map(c => (
                            <option key={c.id || c.name} value={c.id || c.name}>{c.name}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ flex: 1 }}>
                        <label style={{ display: 'block', fontSize: '12px', color: '#64748b', marginBottom: '4px' }}>Porcentaje</label>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={alloc.percentage}
                            onChange={e => updateAllocation(i, 'percentage', e.target.value)}
                            style={{ flex: 1 }}
                          />
                          <span style={{ width: '50px', textAlign: 'right', fontWeight: '600', color: '#1e293b' }}>
                            {alloc.percentage}%
                          </span>
                        </div>
                      </div>
                      {allocations.length > 1 && (
                        <button
                          onClick={() => removeAllocation(i)}
                          style={{
                            padding: '6px',
                            background: 'none',
                            border: 'none',
                            color: '#ef4444',
                            cursor: 'pointer',
                            fontSize: '16px'
                          }}
                        >
                          ✕
                        </button>
                      )}
                    </div>
                    {alloc.percentage > 0 && (
                      <div style={{ marginTop: '8px', fontSize: '13px', color: '#64748b', fontFamily: 'monospace' }}>
                        = {formatCurrency(amount * (alloc.percentage / 100))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Total Indicator */}
              <div style={{
                marginTop: '16px',
                padding: '12px 16px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontWeight: '600',
                backgroundColor: totalPercentage === 100 ? '#ecfdf5' : '#fef2f2',
                color: totalPercentage === 100 ? '#10b981' : '#ef4444'
              }}>
                <span>Total asignado</span>
                <span>{totalPercentage}%</span>
              </div>
            </div>

            {/* Footer */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '16px 20px',
              borderTop: '1px solid #f1f5f9',
              backgroundColor: '#fafafa'
            }}>
              <button
                onClick={excludeTransaction}
                disabled={saving}
                style={{
                  padding: '10px 16px',
                  background: 'none',
                  border: 'none',
                  color: '#ef4444',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: 'pointer'
                }}
              >
                Excluir
              </button>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => setSelectedTx(null)}
                  style={{
                    padding: '10px 16px',
                    backgroundColor: 'white',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    color: '#64748b',
                    fontSize: '14px',
                    cursor: 'pointer'
                  }}
                >
                  Cancelar
                </button>
                <button
                  onClick={saveAssignment}
                  disabled={!isValid || saving}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: isValid ? '#3b82f6' : '#94a3b8',
                    border: 'none',
                    borderRadius: '8px',
                    color: 'white',
                    fontSize: '14px',
                    fontWeight: '600',
                    cursor: isValid && !saving ? 'pointer' : 'not-allowed'
                  }}
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

const formSelectStyle = {
  width: '100%',
  padding: '8px 10px',
  border: '1px solid #e2e8f0',
  borderRadius: '6px',
  fontSize: '13px',
  backgroundColor: 'white'
};
