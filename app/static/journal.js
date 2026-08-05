const journalEls = {
  root: document.querySelector('#journal-zero'),
  brief: document.querySelector('#journal-return-brief'),
  edition: document.querySelector('#journal-edition'),
  archive: document.querySelector('#journal-archive'),
  status: document.querySelector('#journal-status'),
  intelligence: document.querySelector('#intelligence-status'),
};

const JOURNAL_STORAGE_KEY = 'cidade-zero-last-event-id';
const journalSession = {
  previousEventId: Number(localStorage.getItem(JOURNAL_STORAGE_KEY) || 0),
  latestEventId: 0,
};

function journalEscape(value = '') {
  return String(value).replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[character]));
}

async function journalFetch(path) {
  const response = await fetch(path, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

function journalTime(minute) {
  const value = Number(minute) || 0;
  return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`;
}

function renderReturnBrief(brief) {
  if (!journalEls.brief) return;
  if (!brief.has_updates || journalSession.previousEventId === 0) {
    journalEls.brief.innerHTML = `
      <span class="journal-kicker">ACOMPANHAMENTO</span>
      <strong>${journalSession.previousEventId === 0 ? 'Primeira visita registrada' : 'Você está em dia'}</strong>
      <p>${journalSession.previousEventId === 0
        ? 'A partir de agora, o Jornal Zero destacará o que aconteceu desde sua última visita.'
        : 'Nenhum novo acontecimento relevante foi registrado desde sua última passagem.'}</p>`;
    return;
  }

  const highlights = (brief.highlights || []).slice(0, 4).map(item => `
    <li>
      <time>Dia ${item.city_day} · ${journalTime(item.city_minute)}</time>
      <span>${journalEscape(item.summary)}</span>
    </li>`).join('');

  journalEls.brief.innerHTML = `
    <span class="journal-kicker">DESDE SUA ÚLTIMA VISITA</span>
    <strong>${brief.event_count} novos registros entre os dias ${brief.from_day} e ${brief.to_day}</strong>
    ${highlights ? `<ul>${highlights}</ul>` : '<p>A rotina mudou, mas nenhum fato ultrapassou o nível de destaque do jornal.</p>'}`;
}

function renderEdition(edition) {
  if (!journalEls.edition) return;
  const articles = (edition.articles || []).map((article, index) => `
    <article class="journal-article ${index === 0 ? 'journal-lead' : ''}">
      <div class="journal-article-meta">
        <span>${journalEscape(article.category || 'Cidade')}</span>
        <small>${(article.event_ids || []).length} registro(s) verificado(s)</small>
      </div>
      <h3>${journalEscape(article.title)}</h3>
      <p class="journal-lead-text">${journalEscape(article.lead)}</p>
      <p>${journalEscape(article.body)}</p>
    </article>`).join('');

  journalEls.edition.innerHTML = `
    <header class="journal-edition-header">
      <div>
        <span class="journal-kicker">EDIÇÃO DO DIA ${edition.city_day}</span>
        <h3>${journalEscape(edition.title)}</h3>
      </div>
      <span class="journal-method">${edition.ai_generated ? 'redação assistida por IA' : 'redação factual local'}</span>
    </header>
    <p class="journal-edition-summary">${journalEscape(edition.summary)}</p>
    <div class="journal-articles">${articles}</div>`;
}

function renderArchive(editions) {
  if (!journalEls.archive) return;
  journalEls.archive.innerHTML = (editions || []).map(edition => `
    <button type="button" data-journal-day="${edition.city_day}">
      <span>Dia ${edition.city_day}</span>
      <strong>${journalEscape(edition.title)}</strong>
    </button>`).join('');

  journalEls.archive.querySelectorAll('[data-journal-day]').forEach(button => {
    button.addEventListener('click', async () => {
      try {
        const edition = await journalFetch(`/api/journal/editions/${button.dataset.journalDay}`);
        renderEdition(edition);
        journalEls.root?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } catch (error) {
        journalEls.status.textContent = 'Não foi possível abrir essa edição.';
      }
    });
  });
}

async function loadJournal() {
  if (!journalEls.root) return;
  try {
    const [edition, brief, archive, intelligence] = await Promise.all([
      journalFetch('/api/journal'),
      journalFetch(`/api/journal/since?after_event_id=${journalSession.previousEventId}`),
      journalFetch('/api/journal/editions?limit=12'),
      journalFetch('/api/intelligence'),
    ]);
    journalSession.latestEventId = Number(brief.latest_event_id || 0);
    renderReturnBrief(brief);
    renderEdition(edition);
    renderArchive(archive);
    journalEls.status.textContent = `Arquivo atualizado até o Dia ${edition.city_day}`;
    journalEls.intelligence.textContent = intelligence.enabled
      ? `${intelligence.model} · ${intelligence.calls}/${intelligence.max_calls_per_day} chamadas hoje`
      : 'IA ainda não ativada · motor local em funcionamento';
  } catch (error) {
    console.error('Falha ao carregar Jornal Zero', error);
    journalEls.status.textContent = 'Jornal temporariamente indisponível.';
    journalEls.edition.innerHTML = '<p class="journal-empty">A cidade continua funcionando; tente abrir o jornal novamente em instantes.</p>';
  }
}

window.addEventListener('pagehide', () => {
  if (journalSession.latestEventId > 0) {
    localStorage.setItem(JOURNAL_STORAGE_KEY, String(journalSession.latestEventId));
  }
});

loadJournal();
window.setInterval(loadJournal, 60000);
