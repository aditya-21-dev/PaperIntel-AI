const iconPaths = {
  activity: <><path d="M3 12h4l3-8 4 16 3-8h4" /></>,
  arrowRight: <><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></>,
  bookOpen: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" /></>,
  brain: <><path d="M9.5 3a3 3 0 0 0-5.8 1A3.5 3.5 0 0 0 4 10.9 3.5 3.5 0 0 0 7 17v1a3 3 0 0 0 5 2.2" /><path d="M14.5 3a3 3 0 0 1 5.8 1A3.5 3.5 0 0 1 20 10.9 3.5 3.5 0 0 1 17 17v1a3 3 0 0 1-5 2.2" /><path d="M12 2v20" /><path d="M8 7h4M12 14h4" /></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 11h18" /></>,
  chart: <><path d="M3 3v18h18" /><path d="m7 16 4-5 3 3 6-8" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  chevronDown: <path d="m6 9 6 6 6-6" />,
  circleCheck: <><circle cx="12" cy="12" r="9" /><path d="m8 12 2.5 2.5L16 9" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  document: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" /><path d="M14 2v6h6M8 13h8M8 17h6" /></>,
  download: <><path d="M12 3v12" /><path d="m7 10 5 5 5-5" /><path d="M5 21h14" /></>,
  fileSearch: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h8" /><path d="M14 2v6h6" /><circle cx="16.5" cy="16.5" r="3.5" /><path d="m19 19 3 3" /></>,
  filter: <><path d="M4 5h16M7 12h10M10 19h4" /></>,
  grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></>,
  layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 12 9 5 9-5M3 16l9 5 9-5" /></>,
  link: <><path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.2 1.2" /><path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.2-1.2" /></>,
  list: <><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" /></>,
  menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
  paperclip: <><path d="m20.5 11.5-8.6 8.6a5 5 0 0 1-7.1-7.1l8.6-8.6a3.5 3.5 0 1 1 5 5L9.8 18a2 2 0 1 1-2.8-2.8l8.1-8.1" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
  shield: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /><path d="m9 12 2 2 4-4" /></>,
  sparkles: <><path d="m12 3-1.1 4.1L7 8.2l3.9 1.1L12 13l1.1-3.7L17 8.2l-3.9-1.1L12 3Z" /><path d="m5 15-.7 2.3L2 18l2.3.7L5 21l.7-2.3L8 18l-2.3-.7L5 15ZM19 14l-.7 2.3L16 17l2.3.7L19 20l.7-2.3L22 17l-2.3-.7L19 14Z" /></>,
  target: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /><path d="M12 2v2M22 12h-2M12 22v-2M2 12h2" /></>,
  upload: <><path d="M12 16V3" /><path d="m7 8 5-5 5 5" /><path d="M5 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5" /></>,
  users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8" /></>,
  warning: <><path d="m10.3 3.9-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3.1l-8-14a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4M12 17h.01" /></>,
}

export default function Icon({ name, className = 'h-5 w-5', strokeWidth = 1.8 }) {
  return (
    <svg aria-hidden="true" className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      {iconPaths[name] || iconPaths.info}
    </svg>
  )
}
