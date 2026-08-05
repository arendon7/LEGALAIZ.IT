'use strict';

const PROFILE = Object.freeze({
  person: 'María Fernanda Gómez Ruiz',
  secondPerson: 'Carlos Andrés Rodríguez Pérez',
  company: 'Soluciones Andinas S.A.S.',
  nit: '901234567-8',
  id: '1020304050',
  email: 'maria.gomez@demo.legalaiz.it',
  phone: '3001234567',
  address: 'Calle 10 # 35-20',
  city: 'Medellín',
  department: 'Antioquia',
  country: 'Colombia',
});

const normalize = value => String(value || '')
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase();

const answered = value => value !== '' && value != null && (!Array.isArray(value) || value.length > 0);

export function isDemoQuestionVisible(question, answers) {
  if (!question?.show_if) return true;
  const condition = question.show_if;
  const current = String(answers?.[condition.field] || '');
  if (Object.prototype.hasOwnProperty.call(condition, 'equals')) return current === String(condition.equals);
  if (Array.isArray(condition.in)) return condition.in.map(String).includes(current);
  return true;
}

function clampNumber(value, question) {
  let result = Number(value);
  if (!Number.isFinite(result)) result = 1;
  if (question.min != null) result = Math.max(result, Number(question.min));
  if (question.max != null) result = Math.min(result, Number(question.max));
  return String(Number.isInteger(result) ? result : Number(result.toFixed(2)));
}

function isoDateFrom(value, days = 0) {
  const date = new Date(`${value}T12:00:00Z`);
  if (Number.isNaN(date.getTime())) return '2026-08-15';
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function findOption(options, patterns) {
  for (const pattern of patterns) {
    const match = options.find(option => pattern.test(normalize(option)));
    if (match != null) return match;
  }
  return null;
}

function selectDemoOption(question) {
  const options = Array.isArray(question.options) ? question.options : [];
  if (!options.length) return '';
  const key = normalize(`${question.id} ${question.label} ${question.section}`);
  const positive = [/^si\b/, /^acepto\b/, /^autorizo\b/, /^confirmo\b/, /de acuerdo/, /verdadero/];
  const negative = [/^no\b/, /^sin\b/, /ningun/, /no aplica/, /no existe/];
  const consent = /consent|autoriza|acepta|confirm|tratamiento de datos|terminos|declaracion/;
  const risk = /urgente|fraude|suplant|clonacion|hurto|embargo|cobro coactivo|proceso judicial|violencia|amenaza|menor de edad|incapacidad|investigacion penal|pagad[oa]|pago total|sancion/;
  const normalStage = /estado procesal|etapa|enforcement|proceso actual/;

  if (consent.test(key)) return findOption(options, positive) || options[0];
  if (normalStage.test(key)) return findOption(options, [/sin proceso/, /sin decision/, /preliminar/, /inicial/]) || findOption(options, negative) || options[0];
  if (risk.test(key)) return findOption(options, negative) || options[0];

  if (/calidad en la que actua|acting.capacity/.test(key)) {
    return findOption(options, [/propietario/, /titular/, /trabajador/, /consumidor/, /arrendatario/, /contratante/]) || options[0];
  }
  if (/tipo de persona|personeria|naturaleza/.test(key)) return findOption(options, [/persona natural/]) || options[0];
  if (/ciudad|municipio|territorio|departamento|pais/.test(key)) return findOption(options, [/medellin/, /antioquia/, /colombia/]) || options[0];
  return options[0];
}

function demoNumber(question) {
  const key = normalize(`${question.id} ${question.label}`);
  if (/salario|honorario|canon|ingreso|remuneracion|valor|monto|precio|cuantia|deuda|obligacion/.test(key)) return clampNumber(4800000, question);
  if (/porcentaje|tasa/.test(key)) return clampNumber(10, question);
  if (/meses|duracion|plazo/.test(key)) return clampNumber(12, question);
  if (/dias/.test(key)) return clampNumber(30, question);
  if (/anos|antiguedad/.test(key)) return clampNumber(2, question);
  if (/cantidad|numero|count|personas|comparendos/.test(key)) return clampNumber(1, question);
  return clampNumber(question.min != null ? question.min : 1, question);
}

function demoDate(question, answers) {
  const key = normalize(`${question.id} ${question.label}`);
  if (question.after_field && answers?.[question.after_field]) return isoDateFrom(answers[question.after_field], 30);
  if (/nacimiento|birth/.test(key)) return '1990-05-12';
  if (/vencimiento|expiry|finalizacion|terminacion|fecha final|hasta/.test(key)) return '2027-08-14';
  if (/inicio|celebracion|firma|vigencia|expedicion/.test(key)) return '2026-08-15';
  if (/hecho|evento|infraccion|compra|reclamo|notificacion|conocimiento|accidente|despido/.test(key)) return '2026-07-15';
  return '2026-08-15';
}

function fitText(value, question) {
  let text = String(value || 'Dato sintético de demostración');
  const min = Number(question.min_length || 0);
  const max = Number(question.max_length || 0);
  while (min && text.length < min) text += ' demo';
  if (max && text.length > max) text = text.slice(0, max).trim();
  return text;
}

function demoText(question) {
  const key = normalize(`${question.id} ${question.label} ${question.section}`);
  const example = String(question.help?.example || '').trim();
  if (question.format === 'email' || /correo|email|e-mail/.test(key)) return PROFILE.email;
  if (/telefono|celular|movil|phone/.test(key)) return PROFILE.phone;
  if (/nit/.test(key)) return PROFILE.nit;
  if (/identificacion|documento de identidad|cedula|requester.id|petitioner.id|worker.id|employee.id|tenant.id|consumer.id/.test(key)) return PROFILE.id;
  if (/razon social|empresa|empleador|contratante|arrendador.*persona juridica|sociedad|compania/.test(key)) return PROFILE.company;
  if (/nombre|peticionario|solicitante|interesado|trabajador|empleado|arrendatario|consumidor|titular|contratista|representante/.test(key)) return /contraparte|segundo|empleador persona natural|arrendador persona natural/.test(key) ? PROFILE.secondPerson : PROFILE.person;
  if (/direccion|domicilio|notificaciones/.test(key)) return PROFILE.address;
  if (/departamento/.test(key)) return PROFILE.department;
  if (/pais|nacionalidad/.test(key)) return PROFILE.country;
  if (/ciudad|municipio|territorio|lugar/.test(key)) return PROFILE.city;
  if (/placa/.test(key)) return 'DEM123';
  if (/hora/.test(key)) return '10:30';
  if (/radicado|comparendo|contrato.*numero|numero.*actuacion|referencia|codigo|serial/.test(key)) return 'DEMO-2026-001';
  if (/cargo|ocupacion|profesion|rol|oficio/.test(key)) return 'Analista de operaciones';
  if (/objeto|servicio|alcance|actividad contratada/.test(key)) return 'Servicios de consultoría y acompañamiento operativo para un proyecto empresarial de demostración.';
  if (/hechos|descripcion|situacion|detalle|motivo|observacion|comentario|pretension|solicitud|resultado buscado/.test(key)) return 'Caso sintético preparado exclusivamente para demostrar el flujo guiado, la generación documental y la revisión profesional de LegalAIZ.it.';
  if (/url|enlace|fuente/.test(key)) return 'https://example.com/legalaiz-demo';
  if (/cuenta bancaria|cuenta/.test(key)) return '000123456789';
  if (/banco|entidad financiera/.test(key)) return 'Banco Demo Colombia';
  if (/correo/.test(key)) return PROFILE.email;
  if (example && example.length <= 180 && !/[<>\[\]{}]/.test(example)) return example;
  return 'Información sintética verificada para la demostración de LegalAIZ.it.';
}

export function demoAnswerForQuestion(question, answers = {}) {
  if (!question) return '';
  if (question.type === 'select') return selectDemoOption(question);
  if (question.type === 'multiselect') {
    const options = Array.isArray(question.options) ? question.options : [];
    return options.length ? [options[0]] : [];
  }
  if (question.type === 'number') return demoNumber(question);
  if (question.type === 'date') return demoDate(question, answers);
  if (question.type === 'textarea') return fitText(demoText(question), question);
  return fitText(demoText(question), question);
}

export function buildDemoAnswers(questions = []) {
  const answers = {};
  for (let pass = 0; pass < 4; pass += 1) {
    for (const question of questions) {
      if (!isDemoQuestionVisible(question, answers) || answered(answers[question.id])) continue;
      answers[question.id] = demoAnswerForQuestion(question, answers);
    }
  }
  for (const question of questions) {
    if (question.type !== 'date' || !question.after_field || !answers[question.after_field] || !answers[question.id]) continue;
    if (String(answers[question.id]) <= String(answers[question.after_field])) answers[question.id] = isoDateFrom(answers[question.after_field], 30);
  }
  return answers;
}

export function demoAnswerSummary(questions = [], answers = {}) {
  const visible = questions.filter(question => isDemoQuestionVisible(question, answers));
  const missingRequired = visible.filter(question => question.required && !answered(answers[question.id]));
  return {
    visibleCount: visible.length,
    answeredCount: visible.filter(question => answered(answers[question.id])).length,
    missingRequired,
  };
}
