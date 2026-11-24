// Where is David? Edit TRAVEL and deploy; the site picks the trip covering today.
// Dates are inclusive YYYY-MM-DD. Outside every trip = HOME.
window.HOME = 'New York';
window.TRAVEL = [
  // { city: 'Tokyo', from: '2026-12-10', to: '2026-12-20' },
];

// ponytail: compares the viewer's local date, so it can be a day off across timezones.
window.whereIsDavid = (today = new Date().toLocaleDateString('en-CA')) => {
  const trips = window.TRAVEL.slice().sort((a, b) => a.from.localeCompare(b.from));
  const now = trips.find(t => t.from <= today && today <= t.to);
  return { city: now ? now.city : window.HOME, trip: now || null, upcoming: trips.filter(t => t.from > today) };
};
