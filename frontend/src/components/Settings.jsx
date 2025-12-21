import { useState } from 'react';
import { formatCurrency } from '../utils/format';

export default function Settings({ clients, projects, teamMembers, categories, onRefresh, showToast, onOpenModal }) {
  const [activePanel, setActivePanel] = useState('general');

  const panels = [
    { id: 'general', label: 'General' },
    { id: 'clients', label: 'Clientes' },
    { id: 'projects', label: 'Proyectos' },
    { id: 'team', label: 'Equipo' },
    { id: 'categories', label: 'Categorias' },
    { id: 'integrations', label: 'Integraciones' },
  ];

  return (
    <div className="animate-fadeIn grid grid-cols-5 gap-6">
      {/* Menu */}
      <div className="col-span-1 space-y-1">
        {panels.map(p => (
          <button
            key={p.id}
            onClick={() => setActivePanel(p.id)}
            className={`w-full text-left px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              activePanel === p.id
                ? 'bg-blue-50 text-blue-600'
                : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="col-span-4 bg-white border border-slate-200 rounded-xl p-6">
        {activePanel === 'general' && <GeneralSettings />}
        {activePanel === 'clients' && (
          <TableSection
            title="Clientes"
            data={clients}
            columns={['Nombre', 'Contacto', 'Email']}
            renderRow={c => (
              <>
                <td className="px-4 py-3 font-medium text-slate-900">{c.name}</td>
                <td className="px-4 py-3 text-slate-600">{c.contact || '-'}</td>
                <td className="px-4 py-3 text-slate-600">{c.email || '-'}</td>
              </>
            )}
            onAdd={() => onOpenModal('add-client')}
          />
        )}
        {activePanel === 'projects' && (
          <TableSection
            title="Proyectos"
            data={projects}
            columns={['Nombre', 'Cliente', 'Estado']}
            renderRow={p => (
              <>
                <td className="px-4 py-3 font-medium text-slate-900">{p.name}</td>
                <td className="px-4 py-3 text-slate-600">{p.client || '-'}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    p.status === 'Active' ? 'bg-emerald-100 text-emerald-700' :
                    p.status === 'Completed' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'
                  }`}>
                    {p.status === 'Active' ? 'Activo' : p.status === 'Completed' ? 'Completado' : 'En Pausa'}
                  </span>
                </td>
              </>
            )}
            onAdd={() => onOpenModal('add-project')}
          />
        )}
        {activePanel === 'team' && (
          <TableSection
            title="Equipo"
            data={teamMembers}
            columns={['Nombre', 'Rol', 'Salario']}
            renderRow={m => (
              <>
                <td className="px-4 py-3 font-medium text-slate-900">{m.name}</td>
                <td className="px-4 py-3 text-slate-600">{m.role || '-'}</td>
                <td className="px-4 py-3 font-mono text-slate-700">{formatCurrency(m.salary || 0)}</td>
              </>
            )}
            onAdd={() => onOpenModal('add-member')}
          />
        )}
        {activePanel === 'categories' && (
          <TableSection
            title="Categorias"
            data={categories}
            columns={['Nombre', 'Tipo']}
            renderRow={c => (
              <>
                <td className="px-4 py-3 font-medium text-slate-900">{c.name}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    c.type === 'Income' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {c.type === 'Income' ? 'Ingreso' : 'Gasto'}
                  </span>
                </td>
              </>
            )}
            onAdd={() => onOpenModal('add-category')}
          />
        )}
        {activePanel === 'integrations' && <IntegrationsPanel showToast={showToast} />}
      </div>
    </div>
  );
}

function GeneralSettings() {
  const [autoSync, setAutoSync] = useState(true);

  return (
    <div>
      <h3 className="text-lg font-semibold text-slate-900 mb-6">Configuracion General</h3>

      <div className="p-4 bg-slate-50 rounded-xl flex items-center justify-between">
        <div>
          <p className="font-medium text-slate-900">Actualizacion automatica</p>
          <p className="text-sm text-slate-500">Sincronizar datos cada 30 segundos</p>
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={autoSync}
            onChange={e => setAutoSync(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-slate-300 peer-focus:ring-4 peer-focus:ring-blue-100 rounded-full peer peer-checked:after:translate-x-full peer-checked:bg-blue-600 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
        </label>
      </div>
    </div>
  );
}

function TableSection({ title, data, columns, renderRow, onAdd }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
        <button
          onClick={onAdd}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          + Nuevo
        </button>
      </div>

      {data.length === 0 ? (
        <p className="text-slate-400 text-center py-12">No hay {title.toLowerCase()}</p>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-200">
              {columns.map(col => (
                <th key={col} className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">
                  {col}
                </th>
              ))}
              <th className="w-16"></th>
            </tr>
          </thead>
          <tbody>
            {data.map((item, i) => (
              <tr key={item.id || i} className="border-b border-slate-100 hover:bg-slate-50">
                {renderRow(item)}
                <td className="px-4 py-3">
                  <button className="text-sm text-red-500 hover:underline">Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function IntegrationsPanel({ showToast }) {
  const syncQonto = async () => {
    showToast('Sincronizando con Qonto...', 'info');
    try {
      const response = await fetch('/api/sync', { method: 'POST' });
      if (response.ok) {
        showToast('Sincronizacion completada', 'success');
      } else {
        throw new Error('Failed');
      }
    } catch {
      showToast('Error al sincronizar', 'error');
    }
  };

  return (
    <div>
      <h3 className="text-lg font-semibold text-slate-900 mb-6">Integraciones</h3>

      <div className="grid grid-cols-2 gap-4">
        <IntegrationCard
          name="Qonto"
          icon="Q"
          iconClass="bg-black text-white"
          status="Conectado"
          onAction={syncQonto}
          actionLabel="Sincronizar"
        />
        <IntegrationCard
          name="Airtable"
          icon="A"
          iconClass="bg-amber-400 text-white"
          status="Conectado"
          actionLabel="Probar"
        />
      </div>
    </div>
  );
}

function IntegrationCard({ name, icon, iconClass, status, onAction, actionLabel }) {
  return (
    <div className="p-4 bg-slate-50 rounded-xl flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-xl font-bold ${iconClass}`}>
        {icon}
      </div>
      <div className="flex-1">
        <p className="font-semibold text-slate-900">{name}</p>
        <p className="text-sm text-emerald-600">{status}</p>
      </div>
      <button
        onClick={onAction}
        className="px-4 py-2 border border-slate-200 text-sm font-medium rounded-lg hover:bg-white transition-colors"
      >
        {actionLabel}
      </button>
    </div>
  );
}
