// Where is David? Trips come live from Finance Hub via /where; TRAVEL below is
// only the fallback when that's unreachable. Dates are inclusive YYYY-MM-DD;
// `to: null` = ongoing. Outside every trip = HOME.
window.HOME = 'New York';
window.TRAVEL = [];

// ponytail: compares the viewer's local date, so it can be a day off across timezones.
window.whereIsDavid = (today = new Date().toLocaleDateString('en-CA')) => {
  const trips = window.TRAVEL.slice().sort((a, b) => a.from.localeCompare(b.from));
  const now = trips.find(t => t.from <= today && (!t.to || today <= t.to));
  return { city: now ? now.city : window.HOME, trip: now || null, upcoming: trips.filter(t => t.from > today) };
};

window.loadWhere = async () => {
  const local = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  try {
    const d = await (await fetch((local ? 'http://localhost:8001' : '/api/analytics') + '/where')).json();
    if (Array.isArray(d.trips)) window.TRAVEL = d.trips;
  } catch (_) {}
  return window.whereIsDavid();
};
