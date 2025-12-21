import { useMemo, useState } from 'react';
import { formatCurrency, formatPercent, isIncome } from '../utils/format';

export default function Profitability({ transactions, projects, clients }) {
  const [tab, setTab] = useState('clients');

  // Client profitability
  const clientData = useMemo(() => {
    const data = {};
    transactions.forEach(t => {
      const client = t.client || t.client_id;
      if (!client) return;
      const info = clients.find(c => c.id === client || c.name === client);
      const name = info?.name || (client.startsWith('rec') ? 'Cliente' : client);
      if (!data[client]) {
        data[client] = { name, income: 0, expenses: 0 };
      }
      if (isIncome(t)) {
        data[client].income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        data[client].expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });
    return Object.values(data)
      .map(c => ({
        ...c,
        net: c.income - c.expenses,
        margin: c.income > 0 ? ((c.income - c.expenses) / c.income) * 100 : 0
      }))
      .sort((a, b) => b.income - a.income);
  }, [transactions, clients]);

  // Project profitability
  const projectData = useMemo(() => {
    const data = {};
    transactions.forEach(t => {
      const proj = t.project || t.project_id;
      if (!proj) return;
      const info = projects.find(p => p.id === proj || p.name === proj);
      const name = info?.name || (proj.startsWith('rec') ? 'Proyecto' : proj);
      const client = info?.client || '';
      if (!data[proj]) {
        data[proj] = { name, client, income: 0, expenses: 0 };
      }
      if (isIncome(t)) {
        data[proj].income += Math.abs(parseFloat(t.amount) || 0);
      } else {
        data[proj].expenses += Math.abs(parseFloat(t.amount) || 0);
      }
    });
    return Object.values(data)
      .map(p => ({
        ...p,
        net: p.income - p.expenses,
        margin: p.income > 0 ? ((p.income - p.expenses) / p.income) * 100 : 0
      }))
      .sort((a, b) => b.income - a.income);
  }, [transactions, projects]);

  // Summary stats
  const summary = useMemo(() => {
    const items = tab === 'clients' ? clientData : projectData;
    const totalIncome = items.reduce((sum, i) => sum + i.income, 0);
    const totalExpenses = items.reduce((sum, i) => sum + i.expenses, 0);
    const totalNet = totalIncome - totalExpenses;
    const avgMargin = totalIncome > 0 ? (totalNet / totalIncome) * 100 : 0;
    const profitable = items.filter(i => i.margin > 0).length;
    return { totalIncome, totalExpenses, totalNet, avgMargin, profitable, total: items.length };
  }, [tab, clientData, projectData]);

  const items = tab === 'clients' ? clientData : projectData;

  // Styles
  const cardStyle = {
    backgroundColor: 'white',
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
  };

  const tabStyle = (active) => ({
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: '600',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    backgroundColor: active ? 'white' : 'transparent',
    color: active ? '#1e293b' : '#64748b',
    boxShadow: active ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
    transition: 'all 0.15s'
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header with Tabs */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{
          display: 'flex',
          gap: '4px',
          padding: '4px',
          backgroundColor: '#f1f5f9',
          borderRadius: '10px'
        }}>
          <button onClick={() => setTab('clients')} style={tabStyle(tab === 'clients')}>
            Por Cliente
          </button>
          <button onClick={() => setTab('projects')} style={tabStyle(tab === 'projects')}>
            Por Proyecto
          </button>
        </div>

        <div style={{ fontSize: '14px', color: '#64748b' }}>
          {items.length} {tab === 'clients' ? 'clientes' : 'proyectos'} con transacciones
        </div>
      </div>

      {/* Summary Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '16px' }}>
        <SummaryCard
          label="Ingresos Totales"
          value={formatCurrency(summary.totalIncome, true)}
          color="#10b981"
          bgColor="#ecfdf5"
        />
        <SummaryCard
          label="Gastos Totales"
          value={formatCurrency(summary.totalExpenses, true)}
          color="#ef4444"
          bgColor="#fef2f2"
        />
        <SummaryCard
          label="Resultado Neto"
          value={formatCurrency(summary.totalNet, true)}
          color={summary.totalNet >= 0 ? '#3b82f6' : '#ef4444'}
          bgColor={summary.totalNet >= 0 ? '#eff6ff' : '#fef2f2'}
        />
        <SummaryCard
          label="Margen Promedio"
          value={`${summary.avgMargin.toFixed(1)}%`}
          color={summary.avgMargin >= 20 ? '#10b981' : summary.avgMargin >= 0 ? '#f59e0b' : '#ef4444'}
          bgColor={summary.avgMargin >= 20 ? '#ecfdf5' : summary.avgMargin >= 0 ? '#fffbeb' : '#fef2f2'}
        />
        <SummaryCard
          label="Rentables"
          value={`${summary.profitable}/${summary.total}`}
          color="#8b5cf6"
          bgColor="#f5f3ff"
        />
      </div>

      {/* Profit Cards Grid */}
      {items.length === 0 ? (
        <div style={{
          ...cardStyle,
          padding: '64px',
          textAlign: 'center',
          color: '#94a3b8'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📊</div>
          <div style={{ fontSize: '16px', fontWeight: '500' }}>No hay datos para mostrar</div>
          <div style={{ fontSize: '14px', marginTop: '8px' }}>
            Asigna transacciones a {tab === 'clients' ? 'clientes' : 'proyectos'} para ver su rentabilidad
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
          {items.map((item, i) => (
            <ProfitCard key={i} item={item} isProject={tab === 'projects'} rank={i + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value, color, bgColor }) {
  return (
    <div style={{
      backgroundColor: bgColor,
      borderRadius: '10px',
      padding: '16px',
      border: `1px solid ${color}15`
    }}>
      <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '4px' }}>{label}</div>
      <div style={{ fontSize: '20px', fontWeight: '700', color: color, fontFamily: 'monospace' }}>
        {value}
      </div>
    </div>
  );
}

function ProfitCard({ item, isProject, rank }) {
  const marginColor = item.margin >= 20 ? '#10b981' : item.margin >= 0 ? '#f59e0b' : '#ef4444';
  const marginBg = item.margin >= 20 ? '#ecfdf5' : item.margin >= 0 ? '#fffbeb' : '#fef2f2';
  const marginLabel = item.margin >= 20 ? 'Excelente' : item.margin >= 0 ? 'Moderado' : 'Negativo';

  const medals = ['🥇', '🥈', '🥉'];

  return (
    <div style={{
      backgroundColor: 'white',
      borderRadius: '12px',
      border: '1px solid #e2e8f0',
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      overflow: 'hidden',
      transition: 'all 0.15s'
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid #f1f5f9',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px'
      }}>
        <div style={{
          fontSize: '24px',
          width: '32px',
          textAlign: 'center'
        }}>
          {rank <= 3 ? medals[rank - 1] : <span style={{ color: '#94a3b8', fontSize: '14px', fontWeight: '600' }}>#{rank}</span>}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontWeight: '600',
            fontSize: '15px',
            color: '#1e293b',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap'
          }}>
            {item.name}
          </div>
          {isProject && item.client && (
            <div style={{ fontSize: '13px', color: '#64748b', marginTop: '2px' }}>
              {item.client}
            </div>
          )}
        </div>
        <div style={{
          padding: '6px 12px',
          backgroundColor: marginBg,
          borderRadius: '20px',
          textAlign: 'center'
        }}>
          <div style={{
            fontSize: '18px',
            fontWeight: '700',
            fontFamily: 'monospace',
            color: marginColor
          }}>
            {item.margin.toFixed(1)}%
          </div>
          <div style={{ fontSize: '10px', color: marginColor, fontWeight: '500' }}>
            {marginLabel}
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div style={{ padding: '16px 20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '16px' }}>
          <MetricBox label="Ingresos" value={formatCurrency(item.income, true)} color="#10b981" />
          <MetricBox label="Gastos" value={formatCurrency(item.expenses, true)} color="#ef4444" />
          <MetricBox label="Neto" value={formatCurrency(item.net, true)} color={item.net >= 0 ? '#3b82f6' : '#ef4444'} />
        </div>

        {/* Progress Bar */}
        <div style={{
          height: '6px',
          backgroundColor: '#f1f5f9',
          borderRadius: '3px',
          overflow: 'hidden'
        }}>
          <div style={{
            height: '100%',
            width: `${Math.min(Math.max(item.margin, 0), 100)}%`,
            backgroundColor: marginColor,
            borderRadius: '3px',
            transition: 'width 0.3s'
          }} />
        </div>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginTop: '6px',
          fontSize: '11px',
          color: '#94a3b8'
        }}>
          <span>0%</span>
          <span>Margen objetivo: 20%</span>
          <span>100%</span>
        </div>
      </div>
    </div>
  );
}

function MetricBox({ label, value, color }) {
  return (
    <div style={{
      padding: '10px',
      backgroundColor: '#f8fafc',
      borderRadius: '8px',
      textAlign: 'center'
    }}>
      <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>{label}</div>
      <div style={{
        fontSize: '13px',
        fontWeight: '600',
        fontFamily: 'monospace',
        color: color
      }}>
        {value}
      </div>
    </div>
  );
}
