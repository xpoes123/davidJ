// Shared site data. Loaded by index.html, archive.html, writing.html, reading.html.
// Adding content:
//   - new cube: push into the appropriate stack's `cubes` array (newest first)
//   - new column: add a new stack object (must keep plane partition rules: heights weakly decreasing in both i and j)
window.STACKS = [
  {
    i: 0, j: 0, label: 'Projects', color: '#c97c5d',
    archiveHref: 'archive.html?stack=projects',
    sub: "Things I've shipped. A growing catalog of side projects, bots, and small useful tools.",
    cubes: [
      { id: 'sentinel', title: 'Sentinel', subtitle: 'autonomous engineering bot', body: 'Writes, reviews, and deploys code from GitHub issues.', date: '2025-11' },
      { id: 'sage', title: 'Sage', subtitle: 'personal AI assistant', body: 'Calendar, email, reminders, news. A Discord-native daily companion.', date: '2025-08' },
      { id: 'stavid', title: 'Stavid', subtitle: 'apartment life bot', body: 'Budget, habits, and lists, built with Stephanie.', date: '2025-06' },
      { id: 'daytour', title: 'DayTour', subtitle: 'multi-stop day itinerary planner', body: 'A web app for planning, organizing, and visualizing multi-stop day itineraries. Construct and rearrange a sequence of locations for a single day in one place.', href: 'https://github.com/xpoes123/DayTour', date: '2025-04' },
      { id: 'sonder', title: 'Sonder', subtitle: 'music recommender via "song profiles"', body: 'An experimental app where you swipe on dating-profile-style songs to express musical preferences; a clustering engine then recommends new tracks based on inferred taste attributes.', href: 'https://github.com/xpoes123/Sonder', date: '2025-02' },
      { id: 'sharplab', title: 'SharpLab', subtitle: 'sports betting quant lab', body: 'Odds ingestion + CLV tracking for live sports markets.', date: '2026-11' },
      { id: 'nba', title: 'NBA Modeling', subtitle: 'player ratings & spread prediction', body: 'Hybrid RAPM + Elo player ratings feeding a spread model.', date: '2024-03' }
    ]
  },
  {
    i: 1, j: 0, label: 'Research', color: '#6d83a5',
    archiveHref: 'archive.html?stack=research',
    sub: 'Papers from college, mostly combinatorics with detours through dynamical systems and folding.',
    cubes: [
      { id: 'latent', title: 'Latent', subtitle: 'an essay on latent structure', href: 'papers/latent.pdf', date: '2024-08' },
      { id: 'orgi', title: 'Origami', subtitle: 'folds & flat-foldability', href: 'papers/orgi.pdf', date: '2023-12' },
      { id: 'poker', title: 'Poker', subtitle: 'combinatorics from Indiana REU', href: 'papers/poker.pdf', date: '2023-08' },
      { id: 'pp', title: 'Plane Partitions', subtitle: 'asymptotics & bijections', href: 'papers/plane_partition.pdf', date: '2023-05' },
      { id: 'tiling-ferrers', title: 'Tiling Ferrers Boards', subtitle: 'an exposition · arXiv 2312.06698', body: 'A necessary and sufficient condition for a Ferrers board (Young diagram) to be fully tileable with 1×2 dominoes: the board must be 2-colorable such that no color is adjacent to its own color. Proven via induction and a graph-theory approach, with all prerequisite background and failed attempts included. Written as exposition during my research on plane partitions.', href: 'https://arxiv.org/abs/2312.06698', date: '2023-04' },
      { id: 'chaos', title: 'Chaos Game', subtitle: 'dynamical systems', href: 'papers/chaos.pdf', date: '2023-03' }
    ]
  },
  {
    i: 2, j: 0, label: 'Social', color: '#7d8da8',
    archiveHref: 'archive.html?stack=social',
    sub: 'Where to find me elsewhere.',
    cubes: [
      { id: 'linkedin',  title: 'LinkedIn',  subtitle: '/in/xpoes',           href: 'https://www.linkedin.com/in/xpoes/' },
      { id: 'spotify',   title: 'Spotify',   subtitle: 'open profile',         href: 'https://open.spotify.com/' },
      { id: 'instagram', title: 'Instagram', subtitle: '@david.jiang1729',    href: 'https://www.instagram.com/david.jiang1729/' },
      { id: 'discord',   title: 'Discord',   subtitle: 'xpoes' },
      { id: 'github',    title: 'GitHub',    subtitle: '@xpoes123',           href: 'https://github.com/xpoes123' }
    ]
  },
  {
    i: 3, j: 0, label: 'Life', color: '#87a878',
    archiveHref: 'archive.html?stack=life',
    sub: 'Roles and schools, newest first.',
    cubes: [
      { id: 'ramp', title: 'Ramp', subtitle: 'demo creator', body: 'Currently making demos at Ramp.', date: '2026-01' },
      { id: 'uncountable', title: 'Uncountable', subtitle: 'implementation engineer · 2025–2026', body: 'Materials informatics platform; implementation engineering.', date: '2025-06' },
      { id: 'indiana-reu', title: 'Indiana REU', subtitle: 'summer 2023', body: 'Research Experience for Undergraduates at Indiana University. Combinatorics.', date: '2023-06' },
      { id: 'uw', title: 'UW–Madison', subtitle: 'CS + Math · 2021–2025', body: 'Computer science and math with detours through Valorant and biochemistry.', date: '2021-09' }
    ]
  },
  {
    i: 0, j: 1, label: 'Reading', color: '#b54c4c',
    archiveHref: 'reading.html',
    sub: 'A reading list. Currently in progress, recently finished, with reviews when I get to them.',
    cubes: [
      { id: 'thinking-in-bets',     title: 'Thinking in Bets',           subtitle: 'Annie Duke',                  body: 'On decision-making under uncertainty. Review coming when I finish.', href: 'book.html?slug=thinking-in-bets',     date: '2026-04' },
      { id: 'logic-sports-betting', title: 'Logic of Sports Betting',    subtitle: 'Ed Miller & Matthew Davidow', body: 'Foundational text for the SharpLab side of things. Review coming.',    href: 'book.html?slug=logic-sports-betting', date: '2026-01' },
      { id: 'pragmatic-programmer', title: 'Pragmatic Programmer',        subtitle: 'Hunt & Thomas',               body: 'A re-read. Review coming.',                                            href: 'book.html?slug=pragmatic-programmer', date: '2025-11' }
    ]
  },
  {
    i: 1, j: 1, label: 'Writing', color: '#d4a955',
    archiveHref: 'writing.html',
    sub: 'Essays & half-thoughts.',
    cubes: [
      { id: 'albums',     title: "Albums of '25", subtitle: 'a yearly ritual',                 href: 'post.html?slug=albums',     date: '2025-12' },
      { id: 'graduating', title: 'Graduating',     subtitle: 'the lie of the four-year arc',   href: 'post.html?slug=graduating', date: '2023-08' }
    ]
  }
];
