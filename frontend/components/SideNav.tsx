'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navItems = [
    { href: '/sessions', label: 'Session Overview', icon: 'M3 12h18' },
    { href: '/traffic', label: 'Traffic Analysis', icon: 'M4 6h16M4 12h16M4 18h16' },
    { href: '/protocols', label: 'Protocol & Flow', icon: 'M4 6h6v6H4zM14 6h6v6h-6zM4 16h6v6H4zM14 16h6v6h-6z' },
    { href: '/anomalies', label: 'Anomalies & ML', icon: 'M12 9v4m0 4h.01M5.5 19h13l-6.5-14z' },
    { href: '/timeline', label: 'Timeline & Forensics', icon: 'M6 4h12M6 8h12M6 12h6' },
];

function isActivePath(pathname: string, href: string) {
    if (href === '/') {
        return pathname === '/';
    }
    return pathname === href || pathname.startsWith(`${href}/`);
    }

    export default function SideNav() {
    const pathname = usePathname();

    return (
        <>
        <aside className="hidden lg:flex w-64 flex-col bg-[#0f141a] border-r border-zinc-800">
            <div className="px-6 py-6 border-b border-zinc-800">
            <Link href="/" className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-teal-600 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                </div>
                <div>
                <div className="text-lg font-bold">Smart Network</div>
                <div className="text-xs text-zinc-400">Traffic Analyzer</div>
                </div>
            </Link>
            </div>

            <nav className="flex-1 px-4 py-6 space-y-2">
            {navItems.map((item) => {
                const isActive = isActivePath(pathname, item.href);
                return (
                <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors border ${
                    isActive
                        ? 'bg-cyan-500/10 text-cyan-200 border-cyan-500/40 shadow-[0_0_0_1px_rgba(34,211,238,0.2)]'
                        : 'text-zinc-300 border-transparent hover:text-white hover:bg-zinc-800/60'
                    }`}
                >
                    <svg
                    className={`w-4 h-4 ${isActive ? 'text-cyan-300' : 'text-zinc-400'}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.icon} />
                    </svg>
                    {item.label}
                </Link>
                );
            })}
            </nav>

            <div className="px-4 py-4 border-t border-zinc-800">
            <Link
                href="/sessions"
                className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors border ${
                isActivePath(pathname, '/sessions')
                    ? 'bg-cyan-500/10 text-cyan-200 border-cyan-500/40'
                    : 'bg-zinc-800/60 text-zinc-200 border-transparent hover:bg-zinc-700/60'
                }`}
            >
                <span>Session Browser</span>
                <span className="text-xs text-zinc-400">View</span>
            </Link>
            <Link
                href="/"
                className={`mt-2 flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors border ${
                isActivePath(pathname, '/')
                    ? 'bg-cyan-500/10 text-cyan-200 border-cyan-500/40'
                    : 'border-zinc-700 text-zinc-300 hover:bg-zinc-800/60'
                }`}
            >
                <span>Upload Capture</span>
                <span className="text-xs text-zinc-400">New</span>
            </Link>
            </div>
        </aside>

        <div className="lg:hidden bg-[#0f141a] border-b border-zinc-800">
            <div className="px-4 py-4 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 to-teal-600 flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                </div>
                <div>
                <div className="text-sm font-semibold">Smart Network</div>
                <div className="text-xs text-zinc-400">Traffic Analyzer</div>
                </div>
            </Link>
            <Link href="/sessions" className="text-xs text-cyan-400">Sessions</Link>
            </div>
            <div className="px-4 pb-4 overflow-x-auto">
            <div className="flex gap-2 min-w-max">
                {navItems.map((item) => {
                const isActive = isActivePath(pathname, item.href);
                return (
                    <Link
                    key={item.href}
                    href={item.href}
                    className={`px-3 py-1.5 rounded-full text-xs border transition-colors ${
                        isActive
                        ? 'border-cyan-400 text-cyan-200 bg-cyan-500/10'
                        : 'text-zinc-300 border-zinc-700 hover:border-cyan-500/60 hover:text-cyan-300'
                    }`}
                    >
                    {item.label}
                    </Link>
                );
                })}
            </div>
            </div>
        </div>
        </>
    );
}
