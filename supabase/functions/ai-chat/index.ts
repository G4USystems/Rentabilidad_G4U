// Supabase Edge Function: AI Chat for Tio Gilito P&L
// Supports multiple AI providers with 150s timeout

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'

const SYSTEM_PROMPT = `Eres un analista financiero experto para Growth4U (G4U), una consultora de Growth y Go-To-Market.

Tu rol es analizar datos financieros y proporcionar insights accionables. Tienes acceso al contexto financiero actual de la empresa.

Directrices:
- Responde siempre en espanol
- Se conciso pero completo
- Usa numeros y porcentajes cuando sea relevante
- Sugiere acciones concretas cuando sea apropiado
- Si no tienes suficiente informacion, pidela

CONTEXTO FINANCIERO ACTUAL:
{context}`

type AIProvider = 'openai' | 'groq' | 'anthropic' | 'gemini' | 'xai'

interface ModelConfig {
  provider: AIProvider
  model: string
  apiKeyEnv: string
  baseUrl: string
}

const MODEL_CONFIGS: Record<string, ModelConfig> = {
  // Groq (Ultra fast, free tier)
  'groq-llama3-70b': { provider: 'groq', model: 'llama-3.3-70b-versatile', apiKeyEnv: 'GROQ_API_KEY', baseUrl: 'https://api.groq.com/openai/v1' },
  'groq-mixtral': { provider: 'groq', model: 'mixtral-8x7b-32768', apiKeyEnv: 'GROQ_API_KEY', baseUrl: 'https://api.groq.com/openai/v1' },

  // OpenAI GPT-5 Series
  'openai-gpt52': { provider: 'openai', model: 'gpt-5.2', apiKeyEnv: 'OPENAI_API_KEY', baseUrl: 'https://api.openai.com/v1' },
  'openai-gpt51': { provider: 'openai', model: 'gpt-5.1', apiKeyEnv: 'OPENAI_API_KEY', baseUrl: 'https://api.openai.com/v1' },
  'openai-gpt51-codex': { provider: 'openai', model: 'gpt-5.1-codex', apiKeyEnv: 'OPENAI_API_KEY', baseUrl: 'https://api.openai.com/v1' },
  'openai-gpt5': { provider: 'openai', model: 'gpt-5', apiKeyEnv: 'OPENAI_API_KEY', baseUrl: 'https://api.openai.com/v1' },

  // OpenAI GPT-4 Series
  'openai-gpt4o': { provider: 'openai', model: 'gpt-4o', apiKeyEnv: 'OPENAI_API_KEY', baseUrl: 'https://api.openai.com/v1' },
  'openai-gpt4o-mini': { provider: 'openai', model: 'gpt-4o-mini', apiKeyEnv: 'OPENAI_API_KEY', baseUrl: 'https://api.openai.com/v1' },
  'openai-gpt41': { provider: 'openai', model: 'gpt-4.1', apiKeyEnv: 'OPENAI_API_KEY', baseUrl: 'https://api.openai.com/v1' },
  'openai-gpt41-mini': { provider: 'openai', model: 'gpt-4.1-mini', apiKeyEnv: 'OPENAI_API_KEY', baseUrl: 'https://api.openai.com/v1' },

  // OpenAI Reasoning Models
  'openai-o3': { provider: 'openai', model: 'o3', apiKeyEnv: 'OPENAI_API_KEY', baseUrl: 'https://api.openai.com/v1' },
  'openai-o3-mini': { provider: 'openai', model: 'o3-mini', apiKeyEnv: 'OPENAI_API_KEY', baseUrl: 'https://api.openai.com/v1' },
  'openai-o4-mini': { provider: 'openai', model: 'o4-mini', apiKeyEnv: 'OPENAI_API_KEY', baseUrl: 'https://api.openai.com/v1' },

  // Anthropic Claude
  'anthropic-opus': { provider: 'anthropic', model: 'claude-opus-4-20250514', apiKeyEnv: 'ANTHROPIC_API_KEY', baseUrl: 'https://api.anthropic.com/v1' },
  'anthropic-sonnet': { provider: 'anthropic', model: 'claude-sonnet-4-20250514', apiKeyEnv: 'ANTHROPIC_API_KEY', baseUrl: 'https://api.anthropic.com/v1' },
  'anthropic-haiku': { provider: 'anthropic', model: 'claude-3-5-haiku-20241022', apiKeyEnv: 'ANTHROPIC_API_KEY', baseUrl: 'https://api.anthropic.com/v1' },

  // Google Gemini
  'gemini-pro': { provider: 'gemini', model: 'gemini-2.0-flash', apiKeyEnv: 'GEMINI_API_KEY', baseUrl: 'https://generativelanguage.googleapis.com/v1beta' },
  'gemini-flash': { provider: 'gemini', model: 'gemini-2.0-flash-lite', apiKeyEnv: 'GEMINI_API_KEY', baseUrl: 'https://generativelanguage.googleapis.com/v1beta' },

  // xAI Grok
  'xai-grok': { provider: 'xai', model: 'grok-2-latest', apiKeyEnv: 'XAI_API_KEY', baseUrl: 'https://api.x.ai/v1' },
}

// Predefined scenarios
const SCENARIOS: Record<string, string> = {
  'projection': 'Analiza los datos financieros y genera una proyeccion para los proximos 3 meses. Incluye ingresos esperados, gastos proyectados y margen estimado. Presenta escenarios optimista, base y pesimista.',
  'anomalies': 'Revisa los datos y detecta cualquier anomalia o gasto inusual. Identifica transacciones que se desvian significativamente del patron normal. Lista los hallazgos por orden de importancia.',
  'trends': 'Analiza las tendencias en ingresos y gastos. Identifica patrones estacionales, crecimiento/decrecimiento, y categorias con mayor variacion. Incluye graficos conceptuales si es util.',
  'optimization': 'Basandote en los gastos actuales, sugiere areas de optimizacion. Prioriza por impacto potencial y facilidad de implementacion. Incluye estimacion de ahorro.',
  'whatif_revenue': 'Simula un escenario donde los ingresos aumentan un 20%. Calcula el impacto en el margen, el punto de equilibrio y recomienda como gestionar el crecimiento.',
  'whatif_cost': 'Simula un escenario donde los costos se reducen un 10%. Identifica que gastos podrian reducirse de forma realista y calcula el impacto en rentabilidad.',
}

async function callOpenAICompatible(
  baseUrl: string,
  apiKey: string,
  model: string,
  systemPrompt: string,
  messages: Array<{role: string, content: string}>,
  isReasoning: boolean = false
): Promise<string> {
  const requestMessages = isReasoning
    ? messages.map((m, i) => i === 0 && m.role === 'user'
        ? { role: 'user', content: `${systemPrompt}\n\n---\n\nUSER REQUEST:\n${m.content}` }
        : m)
    : [{ role: 'system', content: systemPrompt }, ...messages]

  const body: Record<string, unknown> = {
    model,
    messages: requestMessages,
  }

  if (isReasoning) {
    body.max_completion_tokens = 4000
  } else {
    body.temperature = 0.7
    body.max_tokens = 4000
  }

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`API error (${response.status}): ${errorText.slice(0, 500)}`)
  }

  const data = await response.json()
  return data.choices?.[0]?.message?.content || ''
}

async function callAnthropic(
  apiKey: string,
  model: string,
  systemPrompt: string,
  messages: Array<{role: string, content: string}>
): Promise<string> {
  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model,
      max_tokens: 4000,
      system: systemPrompt,
      messages,
    }),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Anthropic API error (${response.status}): ${errorText.slice(0, 500)}`)
  }

  const data = await response.json()
  return data.content?.[0]?.text || ''
}

async function callGemini(
  apiKey: string,
  model: string,
  systemPrompt: string,
  messages: Array<{role: string, content: string}>
): Promise<string> {
  const geminiContents = messages.map((m, i) => ({
    role: m.role === 'assistant' ? 'model' : 'user',
    parts: [{ text: i === 0 ? `${systemPrompt}\n\n---\n\n${m.content}` : m.content }],
  }))

  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: geminiContents,
        generationConfig: {
          temperature: 0.7,
          maxOutputTokens: 4000,
        },
      }),
    }
  )

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Gemini API error (${response.status}): ${errorText.slice(0, 500)}`)
  }

  const data = await response.json()
  return data.candidates?.[0]?.content?.parts?.[0]?.text || ''
}

async function callAI(
  modelId: string,
  messages: Array<{role: string, content: string}>,
  context: string
): Promise<string> {
  const config = MODEL_CONFIGS[modelId]
  if (!config) {
    throw new Error(`Modelo '${modelId}' no configurado`)
  }

  const apiKey = Deno.env.get(config.apiKeyEnv)
  if (!apiKey) {
    throw new Error(`API key no configurada (${config.apiKeyEnv}). Configurala en Supabase Dashboard > Edge Functions > Secrets.`)
  }

  const systemPrompt = SYSTEM_PROMPT.replace('{context}', context)

  switch (config.provider) {
    case 'openai':
    case 'groq':
    case 'xai': {
      const isReasoning = modelId.includes('-o3') || modelId.includes('-o4')
      return callOpenAICompatible(config.baseUrl, apiKey, config.model, systemPrompt, messages, isReasoning)
    }
    case 'anthropic':
      return callAnthropic(apiKey, config.model, systemPrompt, messages)
    case 'gemini':
      return callGemini(apiKey, config.model, systemPrompt, messages)
    default:
      throw new Error(`Proveedor '${config.provider}' no soportado`)
  }
}

serve(async (req) => {
  // CORS headers
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  }

  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { model, messages, context, scenario } = await req.json()

    if (!model) {
      return new Response(
        JSON.stringify({ error: 'Model is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    let finalMessages = messages || []

    // If scenario is provided, use predefined prompt
    if (scenario && SCENARIOS[scenario]) {
      finalMessages = [{ role: 'user', content: SCENARIOS[scenario] }]
    }

    if (finalMessages.length === 0) {
      return new Response(
        JSON.stringify({ error: 'No messages provided' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    console.log(`Calling AI: model=${model}, messages=${finalMessages.length}`)
    const startTime = Date.now()

    const response = await callAI(model, finalMessages, context || '')

    const duration = Date.now() - startTime
    console.log(`AI response received in ${duration}ms`)

    return new Response(
      JSON.stringify({
        response,
        model,
        duration_ms: duration,
        scenario: scenario || null,
      }),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Edge function error:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
