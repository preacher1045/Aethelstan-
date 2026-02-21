interface PaginationProps {
    currentPage: number;
    totalItems: number;
    itemsPerPage: number;
    onPageChange: (page: number) => void;
}

export default function Pagination({ currentPage, totalItems, itemsPerPage, onPageChange }: PaginationProps) {
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    
    if (totalPages <= 1) return null;

    const showingStart = (currentPage - 1) * itemsPerPage + 1;
    const showingEnd = Math.min(currentPage * itemsPerPage, totalItems);

    return (
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-zinc-800">
        <div className="text-xs text-zinc-500">
            Showing {showingStart}-{showingEnd} of {totalItems}
        </div>
        <div className="flex items-center gap-2">
            <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="px-3 py-1 text-xs bg-zinc-800 text-zinc-300 rounded border border-zinc-700 hover:bg-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
            Previous
            </button>
            <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum;
                if (totalPages <= 5) {
                pageNum = i + 1;
                } else if (currentPage <= 3) {
                pageNum = i + 1;
                } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
                } else {
                pageNum = currentPage - 2 + i;
                }
                
                return (
                <button
                    key={pageNum}
                    onClick={() => onPageChange(pageNum)}
                    className={`w-8 h-8 text-xs rounded transition-colors ${
                    currentPage === pageNum
                        ? 'bg-cyan-500 text-white'
                        : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700 border border-zinc-700'
                    }`}
                >
                    {pageNum}
                </button>
                );
            })}
            </div>
            <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="px-3 py-1 text-xs bg-zinc-800 text-zinc-300 rounded border border-zinc-700 hover:bg-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
            Next
            </button>
        </div>
        </div>
    );
}
