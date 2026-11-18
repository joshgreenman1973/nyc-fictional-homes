/* Fictional New Yorkers at home — map, decade chart, list and detail drawer. */
(() => {
  const MEDIA = [
    { k: 'book', label: 'Books', ink: 'sun' },
    { k: 'theater', label: 'Stage', ink: 'rose' },
    { k: 'film', label: 'Film', ink: 'vermilion' },
    { k: 'tv', label: 'Television', ink: 'cyan' },
    { k: 'comics', label: 'Comics', ink: 'mint' },
  ];
  const PREC = {
    address_in_work: { tier: 'exact', label: 'Address given in the work', long: 'The work itself gives a street address.' },
    building_in_work: { tier: 'exact', label: 'Building or corner named in the work', long: 'The work names a real building or an exact street corner.' },
    creator_stated: { tier: 'exact', label: 'Address given by the creator', long: 'The author, playwright or showrunner named the address or building outside the work.' },
    screen_exterior: { tier: 'screen', label: 'Building shown on screen', long: 'The real building filmed as the outside of the home. The story may say something else.' },
    block_inferred: { tier: 'area', label: 'Street or block only', long: 'The work gives a street or block, or readers pinned a building from clues in it. The circle shows the likely area.' },
    neighborhood: { tier: 'area', label: 'Neighborhood only', long: 'Only the neighborhood is known. The circle covers it roughly.' },
    invented: { tier: 'invented', label: 'Invented address', long: 'The address does not exist. The mark sits where the story implies, inside a dashed circle.' },
  };
  const TIERS = [
    { k: 'exact', label: 'Address or building given', sub: 'In the work, or by its creator' },
    { k: 'screen', label: 'Building shown on screen', sub: 'Film and television exteriors' },
    { k: 'area', label: 'Street, block or neighborhood', sub: 'Circle size is the uncertainty' },
    { k: 'invented', label: 'Invented address', sub: 'Placed where the story implies' },
  ];
  const MEDIUM_NOUN = { book: 'book', theater: 'play', film: 'film', tv: 'TV series', comics: 'comic' };

  const css = getComputedStyle(document.documentElement);
  const tok = n => css.getPropertyValue('--' + n).trim();
  const inkOf = m => tok((MEDIA.find(x => x.k === m) || MEDIA[0]).ink);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const yr = r => (r.start === r.end || r.end == null) ? `${r.start}` : `${r.start}–${String(r.end)}`;
  const decadeOf = y => Math.floor(y / 10) * 10;

  const state = { decade: null, media: new Set(MEDIA.map(m => m.k)), q: '', sel: null };
  let ALL = [], byKey = {}, map, mapReady = false;

  // ---------- geometry ----------
  function ring(lat, lon, r, n = 56) {
    const dx = r / (111320 * Math.cos(lat * Math.PI / 180)), dy = r / 110540, pts = [];
    for (let i = 0; i <= n; i++) { const a = (i / n) * 2 * Math.PI; pts.push([lon + dx * Math.cos(a), lat + dy * Math.sin(a)]); }
    return pts;
  }
  function areaRadius(r) {
    const p = r.precision, given = +r.radius_m || 0;
    // drawn sizes are capped so a few very vague homes do not blanket the map; the drawer states the full uncertainty
    const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
    if (p === 'neighborhood') return clamp(given, 350, 800);
    if (p === 'block_inferred') return clamp(given, 80, 300);
    if (p === 'invented') return clamp(given, 120, 400);
    return 0;
  }

  // ---------- filtering ----------
  function overlapsDecade(r, d) { return r.start <= d + 9 && r.end >= d; }
  function matches(r) {
    if (!state.media.has(r.medium)) return false;
    if (state.decade != null && !overlapsDecade(r, state.decade)) return false;
    if (state.q) {
      const hay = [r.character, r.household, r.work, r.creator, r.address, r.neighborhood, r.borough, r.notes].join(' ').toLowerCase();
      if (!state.q.split(/\s+/).every(w => hay.includes(w))) return false;
    }
    return true;
  }
  const filtered = () => ALL.filter(matches);
  // a home is the story's address; when a film or show gives none, its filmed building stands in
  function isHome(r) {
    if (r.kind === 'story') return true;
    const g = byKey[r.home_key] || [];
    return !g.some(x => x.kind === 'story') && g.find(x => x.kind === 'exterior') === r;
  }

  // ---------- opening text ----------
  function writeOpening() {
    const homes = ALL.filter(isHome);
    const works = new Set(ALL.map(r => r.work + '|' + r.medium)).size;
    const byBoro = {};
    homes.forEach(r => { byBoro[r.borough] = (byBoro[r.borough] || 0) + 1; });
    const n = homes.length, man = byBoro.Manhattan || 0, si = byBoro['Staten Island'] || 0;
    const pct = Math.round(100 * man / n);
    const exact = homes.filter(r => PREC[r.precision].tier === 'exact').length;
    const invented = homes.filter(r => r.precision === 'invented').length;
    const pairs = ALL.filter(r => r.kind === 'exterior' && !isHome(r));
    const outside = pairs.filter(r => r.outside_nyc).length;
    const ys = homes.map(r => r.start).filter(Boolean), y0 = Math.min(...ys);
    document.getElementById('span-years').textContent = `Story years ${decadeOf(y0)}s to now`;
    const word = k => ({ Brooklyn: 'Brooklyn', Queens: 'Queens', Bronx: 'the Bronx', 'Staten Island': 'Staten Island' }[k]);
    const outer = ['Brooklyn', 'Queens', 'Bronx', 'Staten Island'].map(b => `${byBoro[b] || 0} in ${word(b)}`).join(', ').replace(/, ([^,]*)$/, ' and $1');
    document.getElementById('finding').textContent =
      `Of ${n} fictional New York homes traced here, ${man} (${pct} percent) are in Manhattan, and ${si === 0 ? 'none' : (si === 1 ? 'one' : si)} ${si === 1 ? 'is' : 'are'} on Staten Island.`;
    document.getElementById('lede').innerHTML =
      `The homes come from <b>${works}</b> novels, stories, plays, films, television series and comics, set from the ${decadeOf(y0)}s to the present. Outside Manhattan there are ${outer}. ` +
      `For <b>${exact}</b> of them the work or its creator gives a street address or names the building. <b>${invented}</b> have addresses that do not exist. ` +
      `In <b>${pairs.length}</b> cases a film or show shows a different building from the one the story names` + (outside ? `, and ${outside} of those buildings are not in New York at all.` : '.');
  }

  // ---------- decade chart ----------
  function drawDecades() {
    const el = document.getElementById('decades');
    const homes = ALL.filter(r => isHome(r) && state.media.has(r.medium));
    const ys = ALL.filter(isHome).map(r => r.start);
    const d0 = decadeOf(Math.min(...ys)), d1 = decadeOf(new Date().getFullYear());
    const decs = []; for (let d = d0; d <= d1; d += 10) decs.push(d);
    const counts = decs.map(d => { const c = {}; MEDIA.forEach(m => c[m.k] = 0); homes.forEach(r => { if (overlapsDecade(r, d)) c[r.medium]++; }); return c; });
    const tot = counts.map(c => Object.values(c).reduce((a, b) => a + b, 0));
    const max = Math.max(1, ...tot);
    const W = Math.max(320, el.clientWidth), H = W < 600 ? 150 : 180, padB = 22, padT = 18;
    const bw = W / decs.length, gap = Math.max(1, Math.min(3, bw * .18));
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Fictional households by decade">`;
    s += `<line class="axis" x1="0" x2="${W}" y1="${H - padB + .5}" y2="${H - padB + .5}"/>`;
    decs.forEach((d, i) => {
      const x = i * bw;
      if (state.decade === d) s += `<rect class="sel" x="${x}" y="0" width="${bw}" height="${H - padB}"/>`;
      let y = H - padB;
      MEDIA.forEach(m => {
        const v = counts[i][m.k]; if (!v) return;
        const h = (H - padB - padT) * v / max;
        y -= h;
        s += `<rect class="bar" x="${x + gap / 2}" y="${y}" width="${Math.max(1, bw - gap)}" height="${h}" fill="${tok(m.ink)}"/>`;
      });
      const step = bw < 14 ? 50 : bw < 26 ? 20 : 10;
      if (d % step === 0 || (step === 50 && i === 0)) s += `<text x="${x + 1}" y="${H - 5}">${d}</text>`;
      s += `<rect class="hit" data-d="${d}" x="${x}" y="0" width="${bw}" height="${H - padB}"><title>${d}s: ${tot[i]}</title></rect>`;
    });
    s += '</svg>';
    el.innerHTML = s;
    el.querySelectorAll('.hit').forEach(h => h.addEventListener('click', () => {
      const d = +h.dataset.d; setDecade(state.decade === d ? null : d);
    }));
  }

  function setDecade(d) {
    state.decade = d;
    document.getElementById('all-years').setAttribute('aria-pressed', d == null ? 'true' : 'false');
    render();
  }

  function writeReadout(rows) {
    const el = document.getElementById('readout');
    if (state.decade == null) { el.textContent = ''; return; }
    const homes = rows.filter(isHome);
    const names = homes.slice().sort((a, b) => (PREC[a.precision].tier === 'exact' ? 0 : 1) - (PREC[b.precision].tier === 'exact' ? 0 : 1)).slice(0, 4).map(r => r.character);
    el.innerHTML = `In the <b>${state.decade}s</b>, ${homes.length} fictional ${homes.length === 1 ? 'household was' : 'households were'} in town` +
      (names.length ? `, among them ${esc(names.join(', ').replace(/, ([^,]*)$/, ' and $1'))}.` : '.');
  }

  // ---------- map ----------
  function geo(rows) {
    const pts = [], areas = [], lines = [];
    const ids = new Set(rows.map(r => r.id));
    rows.forEach(r => {
      if (r.lat == null) return;
      const tier = PREC[r.precision].tier, color = inkOf(r.medium);
      const props = { id: r.id, color, tier, name: r.character, work: r.work };
      pts.push({ type: 'Feature', properties: props, geometry: { type: 'Point', coordinates: [r.lon, r.lat] } });
      const rad = areaRadius(r);
      if (rad) areas.push({ type: 'Feature', properties: props, geometry: { type: 'Polygon', coordinates: [ring(r.lat, r.lon, rad)] } });
    });
    // story-to-exterior connectors
    Object.values(byKey).forEach(group => {
      const st = group.find(r => r.kind === 'story');
      group.filter(r => r.kind === 'exterior').forEach(ex => {
        if (st && st.lat != null && ex.lat != null && (ids.has(st.id) || ids.has(ex.id)))
          lines.push({ type: 'Feature', properties: { color: inkOf(st.medium) }, geometry: { type: 'LineString', coordinates: [[st.lon, st.lat], [ex.lon, ex.lat]] } });
      });
    });
    const fc = f => ({ type: 'FeatureCollection', features: f });
    return { pts: fc(pts), areas: fc(areas), lines: fc(lines) };
  }

  function initMap() {
    map = new maplibregl.Map({
      container: 'map',
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [-73.968, 40.758], zoom: 11.4, minZoom: 9, maxZoom: 18,
      attributionControl: { compact: true }, cooperativeGestures: false,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    map.on('load', () => {
      // quieter basemap: the house black, dimmer labels
      map.getStyle().layers.forEach(l => {
        if (l.type === 'background') map.setPaintProperty(l.id, 'background-color', tok('bg'));
        if (l.type === 'symbol') { try { map.setPaintProperty(l.id, 'text-opacity', 0.55); } catch (e) {} }
      });
      const empty = { type: 'FeatureCollection', features: [] };
      ['areas', 'lines', 'pts'].forEach(s => map.addSource(s, { type: 'geojson', data: empty }));
      map.addLayer({ id: 'area-fill', type: 'fill', source: 'areas', paint: { 'fill-color': ['get', 'color'], 'fill-opacity': ['case', ['==', ['get', 'tier'], 'invented'], 0.04, 0.07] } });
      map.addLayer({ id: 'area-line', type: 'line', source: 'areas', filter: ['!=', ['get', 'tier'], 'invented'], paint: { 'line-color': ['get', 'color'], 'line-opacity': 0.3, 'line-width': 0.8 } });
      map.addLayer({ id: 'area-dash', type: 'line', source: 'areas', filter: ['==', ['get', 'tier'], 'invented'], paint: { 'line-color': ['get', 'color'], 'line-opacity': 0.8, 'line-width': 1.4, 'line-dasharray': [2, 2] } });
      map.addLayer({ id: 'pair', type: 'line', source: 'lines', paint: { 'line-color': ['get', 'color'], 'line-width': 1.2, 'line-opacity': 0.75, 'line-dasharray': [1, 2.5] } });
      const rz = (a, b) => ['interpolate', ['linear'], ['zoom'], 10, a, 15, b];
      map.addLayer({ id: 'pt-screen', type: 'circle', source: 'pts', filter: ['==', ['get', 'tier'], 'screen'], paint: { 'circle-radius': rz(3.6, 7), 'circle-color': tok('bg'), 'circle-stroke-color': ['get', 'color'], 'circle-stroke-width': rz(1.6, 2.4) } });
      map.addLayer({ id: 'pt-soft', type: 'circle', source: 'pts', filter: ['in', ['get', 'tier'], ['literal', ['area', 'invented']]], paint: { 'circle-radius': rz(2, 3.5), 'circle-color': ['get', 'color'], 'circle-opacity': 0.9 } });
      map.addLayer({ id: 'pt-exact', type: 'circle', source: 'pts', filter: ['==', ['get', 'tier'], 'exact'], paint: { 'circle-radius': rz(3.8, 7.5), 'circle-color': ['get', 'color'], 'circle-stroke-color': tok('bg'), 'circle-stroke-width': 1.2 } });
      map.addLayer({ id: 'pt-sel', type: 'circle', source: 'pts', filter: ['==', ['get', 'id'], ''], paint: { 'circle-radius': rz(9, 14), 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-color': tok('fg'), 'circle-stroke-width': 2 } });
      const hov = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
      ['pt-exact', 'pt-screen', 'pt-soft'].forEach(id => {
        map.on('mouseenter', id, e => {
          map.getCanvas().style.cursor = 'pointer';
          const fs = map.queryRenderedFeatures(e.point, { layers: ['pt-exact', 'pt-screen', 'pt-soft'] });
          const seen = new Set(), rows = fs.filter(f => !seen.has(f.properties.id) && seen.add(f.properties.id)).slice(0, 6);
          const first = ALL.find(x => x.id === rows[0].properties.id), t = first && thumbOf(first);
          hov.setLngLat(e.lngLat).setHTML((t ? `<img class="pop" src="${esc(t)}" alt="">` : '') + rows.map(f => `<b>${esc(f.properties.name)}</b> · ${esc(f.properties.work)}`).join('<br>')).addTo(map);
        });
        map.on('mouseleave', id, () => { map.getCanvas().style.cursor = ''; hov.remove(); });
        map.on('click', id, e => { hov.remove(); openRecord(e.features[0].properties.id, false); });
      });
      mapReady = true;
      render();
    });
  }

  function paintMap(rows) {
    if (!mapReady) return;
    const g = geo(rows);
    map.getSource('pts').setData(g.pts);
    map.getSource('areas').setData(g.areas);
    map.getSource('lines').setData(g.lines);
    map.setFilter('pt-sel', ['==', ['get', 'id'], state.sel || '']);
  }

  // ---------- pictures ----------
  let MEDIA_DATA = { works: {}, venues: {} };
  const workMedia = r => MEDIA_DATA.works[`${r.work}|${r.medium}`] || {};
  const twinOf = r => (byKey[r.home_key] || []).find(x => x.id !== r.id);
  function venueOf(r) {
    const own = MEDIA_DATA.venues[r.id];
    if (own) return own;
    const t = twinOf(r);  // a story address with no photo can borrow the filmed building's
    const v = t && t.kind === 'exterior' && !t.outside_nyc ? MEDIA_DATA.venues[t.id] : null;
    return v ? { ...v, borrowed: true } : null;
  }
  function heroOf(r) {
    const w = workMedia(r);
    if (w.still) return { src: w.still, credit: 'Promotional still via TMDB', link: w.tmdb };
    if (w.wiki_img) return { src: w.wiki_img, credit: 'Image from Wikipedia', link: w.wiki };
    if (w.poster) return { src: w.poster, credit: 'Poster via TMDB', link: w.tmdb };
    return null;
  }
  const thumbOf = r => { const v = venueOf(r), h = heroOf(r); return (h && h.src) || (v && v.src) || null; };
  const fromWork = s => /gutenberg|pglaf|standardebooks|wikisource|gutenberg\.net\.au|(^|\/\/)archive\.org\/(details|download|stream|services)/.test(s.url);
  // a scan of a book still in copyright: quote it, name it, but don't send readers to the copy
  const unlinked = s => /(^|\/\/)archive\.org\/(details|download|stream|services)/.test(s.url);
  const srcLine = (s, r) => unlinked(s)
    ? `From the text of ${esc(r.work)}`
    : `${fromWork(s) ? 'From the text of the work, ' : ''}<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(hostOf(s.url))}</a>`;
  function hostOf(u) { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return u; } }
  function snippet(q, n = 26) { const w = String(q || '').split(/\s+/); return w.length > n ? w.slice(0, n).join(' ') + '…' : q; }
  const ph = r => `<span class="ph" style="--c:${inkOf(r.medium)}"><span>${esc((r.character || '?').split(/\s+/).map(w => w[0]).slice(0, 2).join(''))}</span></span>`;

  // ---------- list ----------
  function drawList(rows) {
    const homes = rows.filter(isHome).length;
    document.getElementById('count').textContent = `${homes} ${homes === 1 ? 'home' : 'homes'}` + (rows.length > homes ? `, plus ${rows.length - homes} filmed ${rows.length - homes === 1 ? 'exterior' : 'exteriors'}` : '');
    const el = document.getElementById('list');
    if (!rows.length) { el.innerHTML = '<div class="empty">Nothing matches. Try another decade or clear the search.</div>'; return; }
    el.innerHTML = rows.map(r => {
      const t = thumbOf(r);
      return `
      <button class="rec${state.sel === r.id ? ' sel' : ''}" data-id="${r.id}">
        ${t ? `<img class="th" loading="lazy" src="${esc(t)}" alt="">` : ph(r)}
        <span class="rt">
          <span class="yr">${yr(r)}</span>
          <b><span class="sw" style="background:${inkOf(r.medium)}"></span>${esc(r.character)}${r.kind === 'exterior' ? (isHome(r) ? ' <span class="dim">(building on screen)</span>' : ' <span class="dim">(filmed exterior)</span>') : ''}</b>
          <span class="meta">${esc(r.work)}, ${esc(MEDIUM_NOUN[r.medium])} (${r.work_year ?? ''})</span>
          <span class="meta">${esc(r.address || '')}${r.neighborhood ? ', ' + esc(r.neighborhood) : ''} · ${esc(PREC[r.precision].label.toLowerCase())}</span>
        </span>
      </button>`;
    }).join('');
    el.querySelectorAll('.rec').forEach(b => b.addEventListener('click', () => openRecord(b.dataset.id, true)));
  }

  // ---------- gallery ----------
  let galleryAll = false;
  function drawGallery(rows) {
    const el = document.getElementById('gallery');
    const homes = rows.filter(isHome);
    const withPic = homes.filter(r => thumbOf(r));
    const show = galleryAll ? homes : withPic.slice(0, 48);
    document.getElementById('gal-count').textContent = galleryAll
      ? `All ${homes.length} homes`
      : `${show.length} of ${homes.length} homes, the ones with pictures`;
    document.getElementById('gal-more').hidden = galleryAll || homes.length <= show.length;
    el.innerHTML = show.map(r => {
      const h = heroOf(r), v = venueOf(r), q = r.sources[0];
      const main = (h && h.src) || (v && v.src);
      return `<button class="card" data-id="${r.id}" style="--c:${inkOf(r.medium)}">
        <span class="cimg">${main ? `<img loading="lazy" src="${esc(main)}" alt="">` : ph(r)}
          ${h && v && v.src ? `<img class="inset" loading="lazy" src="${esc(v.src)}" alt="" title="The building">` : ''}</span>
        <span class="cbody">
          <span class="ck"><i></i>${esc(MEDIUM_NOUN[r.medium])}, ${yr(r)}</span>
          <b>${esc(r.character)}</b>
          <span class="cw">${esc(r.work)}</span>
          <span class="ca">${esc(r.address || '')}</span>
          <q>${esc(snippet(q.quote))}</q>
          <span class="cs">${fromWork(q) ? 'From the text' : 'From ' + esc(hostOf(q.url))}</span>
        </span>
      </button>`;
    }).join('');
    el.querySelectorAll('.card').forEach(b => b.addEventListener('click', () => openRecord(b.dataset.id, true)));
  }

  // ---------- drawer ----------
  function markSvg(tier, color, size = 26) {
    const c = size / 2;
    if (tier === 'exact') return `<svg class="mk" width="${size}" height="${size}"><circle cx="${c}" cy="${c}" r="6" fill="${color}"/></svg>`;
    if (tier === 'screen') return `<svg class="mk" width="${size}" height="${size}"><circle cx="${c}" cy="${c}" r="5.5" fill="none" stroke="${color}" stroke-width="2.2"/></svg>`;
    if (tier === 'area') return `<svg class="mk" width="${size}" height="${size}"><circle cx="${c}" cy="${c}" r="${c - 1}" fill="${color}" fill-opacity=".14" stroke="${color}" stroke-opacity=".5"/><circle cx="${c}" cy="${c}" r="2.4" fill="${color}"/></svg>`;
    return `<svg class="mk" width="${size}" height="${size}"><circle cx="${c}" cy="${c}" r="${c - 1}" fill="${color}" fill-opacity=".06" stroke="${color}" stroke-dasharray="3 3" stroke-width="1.4"/><circle cx="${c}" cy="${c}" r="2.4" fill="${color}"/></svg>`;
  }

  function openRecord(id, fly) {
    const r = ALL.find(x => x.id === id); if (!r) return;
    state.sel = id;
    const color = inkOf(r.medium), tier = PREC[r.precision].tier;
    document.getElementById('d-lbl').textContent = `${r.work}, ${MEDIUM_NOUN[r.medium]}${r.creator ? ' by ' + r.creator : ''}, ${r.work_year ?? ''}`;
    document.getElementById('d-title').textContent = r.character + (r.kind === 'exterior' ? ': the building on screen' : '');
    const twin = (byKey[r.home_key] || []).find(x => x.id !== r.id);
    const sameSpot = r.lat == null ? [] : ALL.filter(x => x.id !== r.id && x.lat != null && x.work !== r.work && Math.abs(x.lat - r.lat) < 0.0004 && Math.abs(x.lon - r.lon) < 0.0005);
    const hero = heroOf(r), ven = venueOf(r), wm = workMedia(r), q0 = r.sources[0];
    let h = '';
    if (hero || ven) {
      h += `<div class="pics${hero && ven ? ' two' : ''}">`;
      if (hero) h += `<figure><img src="${esc(hero.src)}" alt=""><figcaption>${esc(r.work)}. <a href="${esc(hero.link || '#')}" target="_blank" rel="noopener">${esc(hero.credit)}</a></figcaption></figure>`;
      if (ven) h += `<figure><img src="${esc(ven.src)}" alt=""><figcaption>${ven.borrowed ? 'The building used on screen' : r.kind === 'exterior' ? 'The building on screen' : 'The building'}: ${esc(ven.title)}. <a href="${esc(ven.link)}" target="_blank" rel="noopener">${esc(ven.credit)}</a></figcaption></figure>`;
      h += `</div>`;
    }
    h += `<blockquote class="big">${esc(q0.quote)}</blockquote>
      <p class="srcl">${srcLine(q0, r)}</p>
      <p class="addr">${esc(r.address || '')}</p>
      <div class="grade">${markSvg(tier, color, 22)}<span>${esc(PREC[r.precision].long)}</span></div>
      <div class="links">
        ${r.lat != null && PREC[r.precision].tier !== 'invented' ? `<a class="srcbtn" target="_blank" rel="noopener" href="https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${r.lat},${r.lon}">See the block on Street View</a>` : ''}
        ${wm.wiki ? `<a class="srcbtn" target="_blank" rel="noopener" href="${esc(wm.wiki)}">The ${esc(MEDIUM_NOUN[r.medium])} on Wikipedia</a>` : ''}
        ${wm.tmdb ? `<a class="srcbtn" target="_blank" rel="noopener" href="${esc(wm.tmdb)}">Cast and stills</a>` : ''}
      </div>
      <dl class="f">
        ${r.household ? `<div><dt>Household</dt><dd>${esc(r.household)}</dd></div>` : ''}
        <div><dt>Lived there</dt><dd>${yr(r)}, in story time</dd></div>
        ${(tier === 'area' || tier === 'invented') && r.radius_m ? `<div><dt>How close the mark is</dt><dd>Within about ${r.radius_m >= 1000 ? (r.radius_m / 1000).toFixed(1).replace(/\.0$/, '') + ' kilometers' : Math.round(r.radius_m / 10) * 10 + ' meters'}</dd></div>` : ''}
        <div><dt>Where</dt><dd>${esc([r.neighborhood, r.borough].filter(Boolean).join(', ')) || '—'}</dd></div>
        ${r.lat != null ? `<div><dt>Placed on the map as</dt><dd>${esc(r.placed_by === 'approx' ? 'placed by hand from the description' : (r.geocode_label || ''))}</dd></div>` : `<div><dt>On the map</dt><dd>Not shown: this building is outside New York City.</dd></div>`}
      </dl>`;
    if (twin) {
      h += `<div class="twin">${twin.kind === 'exterior'
        ? (twin.outside_nyc ? `The building shown on screen is not in New York: ${esc(twin.address || '')}. ` : `On screen, the outside of this home is a different building: ${esc(twin.address || '')}. `) + `<button data-go="${twin.id}">See the filmed exterior</button>`
        : `The story itself puts this home at ${esc(twin.address || '')}. <button data-go="${twin.id}">See the story's address</button>`}</div>`;
    }
    if (r.notes) h += `<div class="narr"><h4>What is known</h4><p>${esc(r.notes)}</p></div>`;
    if (r.sources.length > 1) {
      h += `<div class="narr"><h4>Second source</h4></div>`;
      r.sources.slice(1).forEach(s => {
        h += `<blockquote>${esc(s.quote)}</blockquote><p class="srcl">${srcLine(s, r)}</p>`;
      });
    }
    if (sameSpot.length) h += `<div class="narr"><h4>Also at this address</h4><p class="same">${sameSpot.map(x => `<button data-go="${x.id}">${esc(x.character)}</button> (${esc(x.work)})`).join(', ')}</p></div>`;
    const body = document.getElementById('d-body');
    body.innerHTML = h;
    body.querySelectorAll('[data-go]').forEach(b => b.addEventListener('click', () => openRecord(b.dataset.go, true)));
    const d = document.getElementById('drawer'); d.classList.add('open'); d.setAttribute('aria-hidden', 'false');
    document.querySelectorAll('.rec').forEach(b => b.classList.toggle('sel', b.dataset.id === id));
    if (mapReady) {
      map.setFilter('pt-sel', ['==', ['get', 'id'], id]);
      if (fly && r.lat != null) map.flyTo({ center: [r.lon, r.lat], zoom: Math.max(map.getZoom(), PREC[r.precision].tier === 'area' ? 13.5 : 15), speed: 1.4 });
    }
    try { history.replaceState(null, '', '#' + id); } catch (e) {}
  }
  function closeDrawer() {
    const d = document.getElementById('drawer'); d.classList.remove('open'); d.setAttribute('aria-hidden', 'true');
  }

  // ---------- controls ----------
  function buildControls() {
    document.getElementById('media-keys').innerHTML = MEDIA.map(m => `<span class="key"><i style="background:${tok(m.ink)}"></i>${m.label}</span>`).join('');
    const chips = document.getElementById('media-chips');
    chips.innerHTML = MEDIA.map(m => `<button class="chip" data-m="${m.k}" aria-pressed="true"><i style="background:${tok(m.ink)}"></i>${m.label}</button>`).join('');
    chips.querySelectorAll('.chip').forEach(c => c.addEventListener('click', () => {
      const k = c.dataset.m;
      // first click on a full set isolates that medium; later clicks toggle
      if (state.media.size === MEDIA.length) { state.media = new Set([k]); }
      else if (state.media.has(k)) { state.media.delete(k); if (!state.media.size) state.media = new Set(MEDIA.map(m => m.k)); }
      else state.media.add(k);
      chips.querySelectorAll('.chip').forEach(x => x.setAttribute('aria-pressed', state.media.has(x.dataset.m) ? 'true' : 'false'));
      render();
    }));
    document.getElementById('all-years').addEventListener('click', () => setDecade(null));
    let t; document.getElementById('q').addEventListener('input', e => { clearTimeout(t); t = setTimeout(() => { state.q = e.target.value.trim().toLowerCase(); render(); }, 120); });
    document.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', closeDrawer));
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDrawer(); });
    const fg = tok('fg2');
    document.getElementById('marks').innerHTML = TIERS.map(t => `<span>${markSvg(t.k, fg, 18)}${t.label}</span>`).join('') + `<span><svg class="mk" width="26" height="10"><line x1="1" y1="5" x2="25" y2="5" stroke="${fg}" stroke-width="1.4" stroke-dasharray="1.5 3.5"/></svg>Story address to filmed exterior</span>`;
    document.getElementById('prec-legend').innerHTML = TIERS.map(t => `<div>${markSvg(t.k, tok('sun'), 30)}<p style="margin:0"><b>${t.label}</b><span>${t.sub}</span></p></div>`).join('');
    let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(drawDecades, 150); });
  }

  function render() {
    const rows = filtered();
    drawDecades();
    writeReadout(rows);
    drawList(rows);
    drawGallery(rows);
    paintMap(rows);
  }

  // a picture that fails to load gives way to the initials tile (or, in the drawer and insets, disappears)
  document.addEventListener('error', e => {
    const img = e.target;
    if (!img || img.tagName !== 'IMG') return;
    const host = img.closest('[data-id]'), r = host && ALL.find(x => x.id === host.dataset.id);
    if (r && (img.classList.contains('th') || img.parentElement.classList.contains('cimg')) && !img.classList.contains('inset')) {
      img.outerHTML = ph(r);
    } else {
      (img.closest('figure') || img).remove();
    }
  }, true);

  Promise.all([
    fetch('data/homes.json').then(r => r.json()),
    fetch('data/media.json').then(r => r.ok ? r.json() : null).catch(() => null),
  ]).then(([data, media]) => {
    if (media) MEDIA_DATA = media;
    document.getElementById('gal-more').addEventListener('click', () => { galleryAll = true; render(); });
    ALL = data.filter(r => PREC[r.precision] && MEDIA.some(m => m.k === r.medium));
    ALL.forEach(r => { (byKey[r.home_key] = byKey[r.home_key] || []).push(r); });
    buildControls();
    writeOpening();
    initMap();
    render();
    const h = location.hash.slice(1);
    if (h && ALL.some(r => r.id === h)) setTimeout(() => openRecord(h, true), 600);
  });
})();
