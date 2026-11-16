import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Source = 'file' | 'sql';
type SlideSpec = { id: number; title: string; report_type: string; period: string; period_end: string; indicator: string; chart_type: string };


const MONTHS = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];

function PeriodPicker({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [open, setOpen] = useState(false);
  const [year, setYear] = useState(Number(value.slice(0, 4)) || new Date().getFullYear());
  const match = /^(\d{4})-(0[1-9]|1[0-2])$/.exec(value);
  const selectedMonth = match ? Number(match[2]) - 1 : -1;
  const selectedYear = match ? Number(match[1]) : -1;
  return <div className="period-picker">
    <button type="button" className="period-trigger" aria-label="Выбрать отчетный месяц" aria-expanded={open}
      onClick={() => { setYear(Number(value.slice(0, 4)) || new Date().getFullYear()); setOpen(!open); }}>
      <span>{match ? `${MONTHS[selectedMonth]} ${selectedYear}` : 'Выберите месяц'}</span>
      <span aria-hidden="true">▦</span>
    </button>
    {open && <div className="period-popover" role="group" aria-label="Выбор месяца и года">
      <div className="period-year">
        <button type="button" aria-label="Предыдущий год" onClick={() => setYear(y => y - 1)}>‹</button>
        <strong>{year}</strong>
        <button type="button" aria-label="Следующий год" onClick={() => setYear(y => y + 1)}>›</button>
      </div>
      <div className="period-months">{MONTHS.map((month, index) =>
        <button type="button" key={month} className={year === selectedYear && index === selectedMonth ? 'selected' : ''}
          aria-pressed={year === selectedYear && index === selectedMonth}
          onClick={() => { onChange(`${year}-${String(index + 1).padStart(2, '0')}`); setOpen(false); }}>
          {month}
        </button>
      )}</div>
    </div>}
  </div>;
}

function App() {
  const [source, setSource] = useState<Source>('file');
  const [file, setFile] = useState<File | null>(null);
  const [slideSpecs, setSlideSpecs] = useState<SlideSpec[]>([
    {id: 1, title: 'Выручка: сентябрь', report_type: 'plan_fact', period: '2026-09', period_end: '2026-09', indicator: 'Выручка', chart_type: 'column'},
    {id: 2, title: 'Выручка: октябрь', report_type: 'plan_fact', period: '2026-10', period_end: '2026-10', indicator: 'Выручка', chart_type: 'column'}
  ]);
  const updateSlide = (id: number, field: keyof SlideSpec, value: string) => setSlideSpecs(items => items.map(item => item.id === id ? {...item, [field]: value} : item));
  const addSlide = () => setSlideSpecs(items => [...items, {id: Math.max(0, ...items.map(item => item.id)) + 1, title: '', report_type: 'plan_fact', period: '2026-10', period_end: '2026-10', indicator: '', chart_type: 'column'}]);
  const duplicateSlide = (id: number) => setSlideSpecs(items => {
    if (items.length >= 30) return items;
    const index = items.findIndex(item => item.id === id);
    if (index < 0) return items;
    const copy = {...items[index], id: Math.max(0, ...items.map(item => item.id)) + 1};
    const result = [...items]; result.splice(index + 1, 0, copy); return result;
  });
  const moveSlide = (index: number, delta: number) => setSlideSpecs(items => {
    const target = index + delta;
    if (target < 0 || target >= items.length) return items;
    const result = [...items]; [result[index], result[target]] = [result[target], result[index]]; return result;
  });
  const [expanded, setExpanded] = useState<number | null>(1);

  const [title, setTitle] = useState('Управленческая презентация');
  const [style, setStyle] = useState('corporate');
  const [includeCover, setIncludeCover] = useState(true);
  const [subtitle, setSubtitle] = useState('Финансовые результаты организации');
  const [author, setAuthor] = useState('');
  const [dbUrl, setDbUrl] = useState('sqlite:///sample.db');
  const [query, setQuery] = useState('SELECT period, category, plan, fact FROM finance');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  async function generate(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setMessage('');
    try {
      if (slideSpecs.length < 1 || slideSpecs.length > 30) throw new Error('Добавьте от 1 до 30 диаграмм');
      let response: Response;
      if (source === 'file') {
        if (!file) throw new Error('Выберите CSV, XLSX или SQL-файл');
        if (file.size > 100 * 1000 * 1000) throw new Error('Размер файла превышает 100 МБ');
        const form = new FormData();
        form.append('slides_config', JSON.stringify(slideSpecs.map(({id, ...config}) => config)));
        form.append('file', file); form.append('period', slideSpecs[0].period);
        form.append('title', title); form.append('style', style);
        form.append('include_cover', String(includeCover)); form.append('subtitle', subtitle); form.append('author', author);
        response = await fetch('/api/generate/file', { method: 'POST', body: form });
      } else {
        response = await fetch('/api/generate/sql', { method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ database_url: dbUrl, query, slides_config: slideSpecs.map(({id, ...config}) => config), period: slideSpecs[0].period, title, style, include_cover: includeCover, subtitle, author }) });
      }
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(typeof err.detail === 'string' ? err.detail : `Ошибка HTTP ${response.status}`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a'); link.href = url; link.download = 'report.pptx'; link.click();
      URL.revokeObjectURL(url);
      setMessage('Презентация сформирована и сохранена');
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Неизвестная ошибка'); }
    finally { setBusy(false); }
  }
  return <main className="container"><header><h1>Конструктор управленческих презентаций</h1></header>
    <form onSubmit={generate}><section><h2>1. Источник данных</h2><div className="tabs"><button type="button" className={source === 'file' ? 'active' : ''} onClick={() => setSource('file')}>CSV / XLSX / SQL-файл</button><button type="button" className={source === 'sql' ? 'active' : ''} onClick={() => setSource('sql')}>SQL</button></div>
      {source === 'file' ? <label>Файл с финансовыми показателями<input type="file" accept=".csv,.xlsx,.sql" onChange={e => setFile(e.target.files?.[0] ?? null)} required /></label> : <><label>Строка подключения<input value={dbUrl} onChange={e => setDbUrl(e.target.value)} required /></label><label>SQL-запрос (только SELECT)<textarea value={query} onChange={e => setQuery(e.target.value)} rows={3} required /></label></>}
      <p className="hint">Столбцы: period, category, plan, fact. Для структуры расходов нужен дополнительный столбец kind со значением expense. SQL-файл должен содержать CREATE TABLE и INSERT INTO в синтаксисе SQLite. Максимальный размер файла — 100 МБ.</p></section>
      <section><h2>2. Настройки презентации</h2>
      <label>Название презентации<input value={title} onChange={e => setTitle(e.target.value)} required /></label>
      <label>Стиль оформления PPTX<select value={style} onChange={e => setStyle(e.target.value)}>
        <option value="corporate">Корпоративный (синий)</option><option value="minimal">Минималистичный (светлый)</option><option value="dark">Темный</option>
      </select></label>
      <label className="check"><input type="checkbox" checked={includeCover} onChange={e => setIncludeCover(e.target.checked)} /> Добавить титульный слайд</label>
      {includeCover && <div className="cover-fields"><label>Подзаголовок<input value={subtitle} onChange={e => setSubtitle(e.target.value)} /></label><label>Автор / организация<input value={author} onChange={e => setAuthor(e.target.value)} /></label></div>}
      </section>
      <section><div className="section-heading"><div><h2>3. Конструктор слайдов</h2></div><span className="counter">Текущее количество слайдов: {slideSpecs.length + (includeCover ? 1 : 0)}</span></div>
      <div className="slide-builder">
        {includeCover && <div className="slide-outline cover-outline"><span className="slide-number">1</span><div><strong>Титульный слайд</strong><small>{title}</small></div><span className="muted">Обложка</span></div>}
        {slideSpecs.map((item, index) => <div className="slide-card" key={item.id}>
          <div className="slide-card-head"><button type="button" className="slide-toggle" aria-expanded={expanded === item.id} onClick={() => setExpanded(expanded === item.id ? null : item.id)}><span className="slide-number">{index + (includeCover ? 2 : 1)}</span><span><strong>{item.title.trim() || (item.indicator ? `${item.indicator}: ${item.period}` : `Диаграмма ${index + 1}`)}</strong><small>{item.report_type === 'plan_fact' ? 'План-факт' : item.report_type === 'dynamics' ? 'Динамика' : 'Структура расходов'} · {item.period}{item.report_type === 'dynamics' ? ` — ${item.period_end}` : ''}</small></span><span className="muted">{expanded === item.id ? 'Свернуть' : 'Настроить'} ▾</span></button>
          <div className="slide-actions"><button type="button" title="Вверх" aria-label="Переместить выше" disabled={index === 0} onClick={() => moveSlide(index, -1)}>↑</button><button type="button" title="Вниз" aria-label="Переместить ниже" disabled={index === slideSpecs.length - 1} onClick={() => moveSlide(index, 1)}>↓</button><button type="button" title="Дублировать" aria-label="Дублировать слайд" disabled={slideSpecs.length >= 30} onClick={() => { duplicateSlide(item.id); setExpanded(null); }}>⧉</button><button type="button" title="Удалить" aria-label="Удалить слайд" onClick={() => setSlideSpecs(items => items.filter(x => x.id !== item.id))}>×</button></div></div>
          {expanded === item.id && <div className="slide-fields">
            <label>Заголовок слайда<input value={item.title} onChange={e => updateSlide(item.id, 'title', e.target.value)} placeholder="Автоматический заголовок" /></label>
            <label>Тип анализа<select value={item.report_type} onChange={e => updateSlide(item.id, 'report_type', e.target.value)}><option value="plan_fact">План-факт</option><option value="dynamics">Динамика</option><option value="expenses">Структура расходов</option></select></label>
            <div className="grid"><label>{item.report_type === 'dynamics' ? 'Начало периода' : 'Отчетный период'}<PeriodPicker value={item.period} onChange={v => updateSlide(item.id, 'period', v)} /></label>
            {item.report_type === 'dynamics' && <label>Конец периода<PeriodPicker value={item.period_end} onChange={v => updateSlide(item.id, 'period_end', v)} /></label>}</div>
            <label>{item.report_type === 'expenses' ? 'Статья расходов (необязательно)' : item.report_type === 'dynamics' ? 'Показатель' : 'Показатель (необязательно)'}<input value={item.indicator} onChange={e => updateSlide(item.id, 'indicator', e.target.value)} placeholder="Например, Выручка" /></label>
            {item.report_type === 'plan_fact' && <label>Тип диаграммы<select value={item.chart_type} onChange={e => updateSlide(item.id, 'chart_type', e.target.value)}><option value="column">Вертикальные столбцы</option><option value="bar">Горизонтальные полосы</option><option value="line">Линейный график</option></select></label>}
            {item.report_type !== 'plan_fact' && <p className="hint">{item.report_type === 'dynamics' ? 'Для динамики используется линейный график.' : 'Для структуры расходов используется круговая диаграмма. Требуется kind=expense.'}</p>}
          </div>}
        </div>)}
        <button type="button" className="add-slide" onClick={() => { addSlide(); setExpanded(null); }} disabled={slideSpecs.length >= 30}>＋ Добавить слайд с диаграммой</button>
      </div>
      <p className="hint">Порядок карточек соответствует порядку слайдов в итоговом PPTX. Каждая диаграмма будет редактируемой.</p>
      </section>
      <button className="primary" disabled={busy || slideSpecs.length === 0} type="submit">{busy ? 'Формирование...' : 'Сформировать и скачать PPTX'}</button>
      {message && <p role="status" className="status">{message}</p>}
    </form><footer>Программа выполняет заданные расчеты, но не заменяет финансовый анализ специалиста.</footer></main>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
