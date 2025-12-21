import { useState } from 'react';
import { formatCurrency, formatPercent } from '../utils/format';
import { api } from '../hooks/useApi';

const SCENARIOS = [
  { id: 'growth', icon: '📈', name: 'Crecimiento', desc: 'Proyectar crecimiento de ingresos' },
  { id: 'cost_reduction', icon: '💰', name: 'Reduccion Costos', desc: 'Simular reduccion de gastos' },
  { id: 'new_project', icon: '🚀', name: 'Nuevo Proyecto', desc: 'Impacto de nuevo proyecto' },
  { id: 'custom', icon: '⚙️', name: 'Personalizado', desc: 'Definir parametros custom' },
];

export default function Simulator({ projects, showToast }) {
  const [scenarioType, setScenarioType] = useState('growth');
  const [period, setPeriod] = useState(6);
  const [variation, setVariation] = useState(10);
  const [selectedProject, setSelectedProject] = useState('');
  const [customPrompt, setCustomPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  const runSimulation = async () => {
    setLoading(true);
    try {
      const response = await api.simulate({
        scenario_type: scenarioType,
        months: period,
        variation_percent: variation,
        project_id: selectedProject || null,
        custom_prompt: customPrompt || null,
      });
      setResults(response);
    } catch (error) {
      showToast('Error al ejecutar simulacion: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fadeIn grid grid-cols-2 gap-6 items-start">
      {/* Form */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden sticky top-6">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <h3 className="font-semibold text-slate-900">Simulador de Escenarios</h3>
          <div className="flex items-center gap-1 px-3 py-1 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-full">
            <AIIcon className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-semibold text-blue-600">Potenciado por IA</span>
          </div>
        </div>

        <div className="p-5 space-y-5">
          {/* Scenario Type */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-3">Tipo de Escenario</label>
            <div className="grid grid-cols-2 gap-3">
              {SCENARIOS.map(s => (
                <label
                  key={s.id}
                  className={`cursor-pointer p-4 border-2 rounded-xl transition-all ${
                    scenarioType === s.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="scenario"
                    value={s.id}
                    checked={scenarioType === s.id}
                    onChange={e => setScenarioType(e.target.value)}
                    className="sr-only"
                  />
                  <span className="text-2xl mb-2 block">{s.icon}</span>
                  <span className="font-semibold text-slate-900 block">{s.name}</span>
                  <span className="text-xs text-slate-500">{s.desc}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Period & Variation */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Periodo</label>
              <select
                value={period}
                onChange={e => setPeriod(parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={3}>3 meses</option>
                <option value={6}>6 meses</option>
                <option value={12}>12 meses</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Variacion (%)</label>
              <input
                type="number"
                value={variation}
                onChange={e => setVariation(parseFloat(e.target.value))}
                min={-100}
                max={100}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Project selector (for new_project scenario) */}
          {scenarioType === 'new_project' && (
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Proyecto</label>
              <select
                value={selectedProject}
                onChange={e => setSelectedProject(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Seleccionar proyecto...</option>
                {projects.map(p => (
                  <option key={p.id || p.name} value={p.id || p.name}>{p.name}</option>
                ))}
              </select>
            </div>
          )}

          {/* Custom prompt (for custom scenario) */}
          {scenarioType === 'custom' && (
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Describe tu escenario</label>
              <textarea
                value={customPrompt}
                onChange={e => setCustomPrompt(e.target.value)}
                placeholder="Ej: Que pasaria si aumentamos el precio un 15% y perdemos 10% de clientes?"
                rows={3}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}

          {/* Run Button */}
          <button
            onClick={runSimulation}
            disabled={loading}
            className="w-full py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Procesando...
              </>
            ) : (
              <>
                <PlayIcon className="w-5 h-5" />
                Ejecutar Simulacion
              </>
            )}
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="space-y-6">
        {!results ? (
          <div className="bg-white border border-slate-200 rounded-xl p-16 text-center">
            <ChartIcon className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500">Ejecuta una simulacion para ver los resultados</p>
          </div>
        ) : (
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Resultados de la Simulacion</h3>
            </div>

            <div className="p-5 space-y-4">
              {/* Metrics */}
              <ResultMetric
                label="Ingresos Proyectados"
                value={formatCurrency(results.projected?.income || 0)}
                valueClass="text-emerald-600"
              />
              <ResultMetric
                label="Gastos Proyectados"
                value={formatCurrency(results.projected?.expenses || 0)}
                valueClass="text-red-500"
              />
              <ResultMetric
                label="Resultado Neto"
                value={formatCurrency(results.projected?.net || 0)}
                valueClass={results.projected?.net >= 0 ? 'text-emerald-600' : 'text-red-500'}
              />
              <ResultMetric
                label="Margen Proyectado"
                value={formatPercent(results.projected?.margin || 0)}
                valueClass={results.projected?.margin >= 0 ? 'text-emerald-600' : 'text-red-500'}
              />

              {/* AI Insight */}
              {results.insight && (
                <div className="mt-6 p-4 bg-blue-50 rounded-xl">
                  <div className="flex items-center gap-2 mb-2">
                    <AIIcon className="w-4 h-4 text-blue-600" />
                    <span className="text-xs font-semibold text-blue-600 uppercase">Analisis IA</span>
                  </div>
                  <p className="text-slate-700 leading-relaxed">{results.insight}</p>
                </div>
              )}

              {/* Recommendations */}
              {results.recommendations?.length > 0 && (
                <div className="mt-4 p-4 bg-slate-50 rounded-xl">
                  <p className="text-xs font-semibold text-slate-600 uppercase mb-3">Recomendaciones</p>
                  <ul className="space-y-2">
                    {results.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-2 text-slate-700">
                        <span className="text-blue-500 mt-1">•</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ResultMetric({ label, value, valueClass = '' }) {
  return (
    <div className="flex justify-between items-center p-4 bg-slate-50 rounded-xl">
      <span className="text-slate-600">{label}</span>
      <span className={`text-xl font-bold font-mono ${valueClass}`}>{value}</span>
    </div>
  );
}

function AIIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2a4 4 0 014 4c0 1.1-.9 2-2 2h-4a2 2 0 01-2-2 4 4 0 014-4z"/>
      <path d="M12 8v8M8 12h8"/>
      <circle cx="12" cy="19" r="2"/>
    </svg>
  );
}

function PlayIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="5 3 19 12 5 21 5 3"/>
    </svg>
  );
}

function ChartIcon(props) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M3 3v18h18"/>
      <path d="M7 16l4-4 4 4 5-6"/>
    </svg>
  );
}
