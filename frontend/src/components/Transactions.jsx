import { useMemo, useState } from 'react';
import { formatCurrency, formatDate, isIncome } from '../utils/format';

export default function Transactions({ transactions, projects, clients, onAssign }) {
  const [filters, setFilters] = useState({ type: '', category: '', search: '' });
  const [page, setPage] = useState(1);
  const perPage = 20;

  // Get unique categories
  const categories = useMemo(() => {
    const set = new Set();
    transactions.forEach(t => {
      const cat = t.category || t.qonto_category;
      if (cat) set.add(cat);
    });
    return Array.from(set).sort();
  }, [transactions]);

  // Filter and sort transactions
  const filtered = useMemo(() => {
    return transactions
      .filter(t => {
        if (filters.type === 'income' && !isIncome(t)) return false;
        if (filters.type === 'expense' && isIncome(t)) return false;
        if (filters.category && (t.category || t.qonto_category) !== filters.category) return false;
        if (filters.search) {
          const q = filters.search.toLowerCase();
          const name = (t.counterparty_name || '').toLowerCase();
          const label = (t.label || '').toLowerCase();
          if (!name.includes(q) && !label.includes(q)) return false;
        }
        return true;
      })
      .sort((a, b) => new Date(b.settled_at || b.emitted_at) - new Date(a.settled_at || a.emitted_at));
  }, [transactions, filters]);

  // Stats
  const stats = useMemo(() => {
    let income = 0, expenses = 0, unassigned = 0;
    filtered.forEach(t => {
      const amount = Math.abs(parseFloat(t.amount) || 0);
      if (isIncome(t)) income += amount;
      else expenses += amount;
      if (!t.project && !t.project_id && !t.client && !t.client_id) unassigned++;
    });
    return { total: filtered.length, income, expenses, unassigned };
  }, [filtered]);

  // Pagination
  const totalPages = Math.ceil(filtered.length / perPage);
  const paginated = filtered.slice((page - 1) * perPage, page * perPage);

  const updateFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters({ type: '', category: '', search: '' });
    setPage(1);
  };

  // Styles
  const cardStyle = {
    backgroundColor: 'white',
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
  };

  const statCardStyle = (bgColor, textColor) => ({
    backgroundColor: bgColor,
    borderRadius: '10px',
    padding: '16px',
    textAlign: 'center'
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
        <div style={statCardStyle('#f8fafc', '#1e293b')}>
          <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '4px' }}>Total</div>
          <div style={{ fontSize: '24px', fontWeight: '700' }}>{stats.total}</div>
        </div>
        <div style={statCardStyle('#ecfdf5', '#10b981')}>
          <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '4px' }}>Ingresos</div>
          <div style={{ fontSize: '24px', fontWeight: '700', fontFamily: 'monospace', color: '#10b981' }}>
            {formatCurrency(stats.income, true)}
          </div>
        </div>
        <div style={statCardStyle('#fef2f2', '#ef4444')}>
          <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '4px' }}>Gastos</div>
          <div style={{ fontSize: '24px', fontWeight: '700', fontFamily: 'monospace', color: '#ef4444' }}>
            {formatCurrency(stats.expenses, true)}
          </div>
        </div>
        <div style={statCardStyle('#fffbeb', '#f59e0b')}>
          <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '4px' }}>Sin asignar</div>
          <div style={{ fontSize: '24px', fontWeight: '700', color: '#f59e0b' }}>{stats.unassigned}</div>
        </div>
      </div>

      {/* Filters */}
      <div style={{ ...cardStyle, padding: '16px', display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
        <select
          value={filters.type}
          onChange={e => updateFilter('type', e.target.value)}
          style={selectStyle}
        >
          <option value="">Todos los tipos</option>
          <option value="income">Ingresos</option>
          <option value="expense">Gastos</option>
        </select>

        <select
          value={filters.category}
          onChange={e => updateFilter('category', e.target.value)}
          style={selectStyle}
        >
          <option value="">Todas las categorías</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>

        <input
          type="text"
          placeholder="Buscar..."
          value={filters.search}
          onChange={e => updateFilter('search', e.target.value)}
          style={{
            padding: '8px 12px',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            fontSize: '14px',
            width: '200px',
            outline: 'none'
          }}
        />

        {(filters.type || filters.category || filters.search) && (
          <button onClick={clearFilters} style={linkButtonStyle}>
            Limpiar filtros
          </button>
        )}
      </div>

      {/* Table */}
      <div style={cardStyle}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: '#f8fafc' }}>
              <th style={thStyle}>Fecha</th>
              <th style={thStyle}>Descripción</th>
              <th style={thStyle}>Categoría</th>
              <th style={thStyle}>Proyecto</th>
              <th style={thStyle}>Cliente</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Monto</th>
              <th style={{ ...thStyle, width: '60px' }}></th>
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '48px', color: '#94a3b8' }}>
                  <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔍</div>
                  <div>No hay transacciones</div>
                </td>
              </tr>
            ) : (
              paginated.map(tx => (
                <TransactionRow
                  key={tx.id}
                  tx={tx}
                  projects={projects}
                  clients={clients}
                  onAssign={onAssign}
                />
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 16px',
            borderTop: '1px solid #f1f5f9',
            backgroundColor: '#fafafa'
          }}>
            <span style={{ fontSize: '14px', color: '#64748b' }}>
              {(page - 1) * perPage + 1} - {Math.min(page * perPage, filtered.length)} de {filtered.length}
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                style={paginationBtnStyle(page === 1)}
              >
                ← Anterior
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                style={paginationBtnStyle(page === totalPages)}
              >
                Siguiente →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function TransactionRow({ tx, projects, clients, onAssign }) {
  const amount = Math.abs(parseFloat(tx.amount) || 0);
  const income = isIncome(tx);

  // Resolve project/client names
  const projId = tx.project || tx.project_id;
  const clientId = tx.client || tx.client_id;

  const projInfo = projId ? projects.find(p => p.id === projId || p.name === projId) : null;
  const clientInfo = clientId ? clients.find(c => c.id === clientId || c.name === clientId) : null;

  const projName = projInfo?.name || (projId && !projId.startsWith('rec') ? projId : null);
  const clientName = clientInfo?.name || (clientId && !clientId.startsWith('rec') ? clientId : null);

  const isUnassigned = !projId && !clientId;

  return (
    <tr style={{ borderBottom: '1px solid #f1f5f9', backgroundColor: isUnassigned ? '#fffbeb' : 'white' }}>
      <td style={tdStyle}>
        <span style={{ color: '#64748b', fontSize: '14px' }}>
          {formatDate(tx.settled_at || tx.emitted_at)}
        </span>
      </td>
      <td style={tdStyle}>
        <div style={{ fontWeight: '500', color: '#1e293b', maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {tx.counterparty_name || tx.label || '-'}
        </div>
      </td>
      <td style={tdStyle}>
        <span style={{ fontSize: '13px', color: '#64748b' }}>
          {tx.category || tx.qonto_category || '-'}
        </span>
      </td>
      <td style={tdStyle}>
        {projName ? (
          <span style={{
            display: 'inline-block',
            padding: '4px 8px',
            backgroundColor: '#eff6ff',
            color: '#3b82f6',
            borderRadius: '6px',
            fontSize: '12px',
            fontWeight: '500'
          }}>
            {projName}
          </span>
        ) : (
          <span style={{ color: '#cbd5e1' }}>-</span>
        )}
      </td>
      <td style={tdStyle}>
        <span style={{ fontSize: '14px', color: '#475569' }}>
          {clientName || <span style={{ color: '#cbd5e1' }}>-</span>}
        </span>
      </td>
      <td style={{ ...tdStyle, textAlign: 'right' }}>
        <span style={{
          fontFamily: 'monospace',
          fontWeight: '600',
          color: income ? '#10b981' : '#ef4444'
        }}>
          {income ? '+' : '-'}{formatCurrency(amount)}
        </span>
      </td>
      <td style={tdStyle}>
        <button
          onClick={() => onAssign(tx)}
          style={{
            padding: '6px 10px',
            backgroundColor: 'transparent',
            border: '1px solid #e2e8f0',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '12px',
            color: '#64748b'
          }}
          title="Asignar"
        >
          ✏️
        </button>
      </td>
    </tr>
  );
}

// Styles
const selectStyle = {
  padding: '8px 12px',
  border: '1px solid #e2e8f0',
  borderRadius: '8px',
  fontSize: '14px',
  backgroundColor: 'white',
  cursor: 'pointer',
  outline: 'none'
};

const linkButtonStyle = {
  background: 'none',
  border: 'none',
  color: '#ef4444',
  fontSize: '14px',
  cursor: 'pointer',
  textDecoration: 'underline'
};

const thStyle = {
  textAlign: 'left',
  padding: '12px 16px',
  fontSize: '12px',
  fontWeight: '600',
  color: '#64748b',
  textTransform: 'uppercase',
  letterSpacing: '0.5px'
};

const tdStyle = {
  padding: '12px 16px',
  fontSize: '14px'
};

const paginationBtnStyle = (disabled) => ({
  padding: '8px 16px',
  border: '1px solid #e2e8f0',
  borderRadius: '6px',
  backgroundColor: disabled ? '#f8fafc' : 'white',
  color: disabled ? '#cbd5e1' : '#475569',
  fontSize: '14px',
  cursor: disabled ? 'not-allowed' : 'pointer'
});
