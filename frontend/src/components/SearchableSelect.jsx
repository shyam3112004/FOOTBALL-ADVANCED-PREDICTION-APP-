import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Search, ChevronDown, Check, Globe } from 'lucide-react';

/**
 * SearchableSelect Component
 * A custom dropdown with built-in search/filtering.
 */
export default function SearchableSelect({
  options = [],
  value = '',
  onChange,
  placeholder = 'Search...',
  emptyMessage = 'No results found',
  loading = false,
  disabled = false,
  className = '',
  iconKey = 'emblem',
  labelKey = 'name',
  valueKey = 'code',
  canSelectAll = false,
  onSelectAll = null,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const containerRef = useRef(null);
  const inputRef = useRef(null);

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Reset search when opening
  useEffect(() => {
    if (isOpen) {
      setSearchTerm('');
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const filteredOptions = useMemo(() => {
    if (!searchTerm) return options;
    const term = searchTerm.toLowerCase();
    return options.filter(opt => 
      opt[labelKey]?.toLowerCase().includes(term) || 
      opt.area?.toLowerCase().includes(term)
    );
  }, [options, searchTerm, labelKey]);

  const selectedOption = useMemo(() => 
    options.find(opt => String(opt[valueKey]) === String(value)),
    [options, value, valueKey]
  );

  return (
    <div className={`relative ${className}`} ref={containerRef}>
      {/* Trigger */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between gap-2 bg-bg-elevated border border-[#2D3748] rounded-lg px-3 py-1.5 text-sm transition-all outline-none focus:border-accent-green/50 disabled:opacity-30 disabled:cursor-not-allowed ${
          isOpen ? 'ring-1 ring-accent-green/20' : ''
        }`}
      >
        <div className="flex items-center gap-2 truncate">
          {selectedOption ? (
             <>
               {selectedOption[iconKey] ? (
                 <img src={selectedOption[iconKey]} alt="" className="w-4 h-4 object-contain shrink-0" />
               ) : (
                 <Globe className="w-3.5 h-3.5 text-text-muted shrink-0" />
               )}
               <span className="text-text-primary truncate">{selectedOption[labelKey]}</span>
               {selectedOption.area && (
                 <span className="text-[10px] text-text-muted truncate hidden sm:inline">({selectedOption.area})</span>
               )}
             </>
          ) : (
            <span className="text-text-muted">{placeholder}</span>
          )}
        </div>
        <ChevronDown className={`w-4 h-4 text-text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 z-[100] mt-1 bg-[#1A202C] border border-[#2D3748] rounded-xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
          {/* Search Input */}
          <div className="p-2 border-b border-[#2D3748] bg-bg-primary/50">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
              <input
                ref={inputRef}
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Type to filter..."
                className="w-full bg-bg-elevated border border-[#2D3748] rounded-md pl-8 pr-3 py-1.5 text-xs text-text-primary outline-none focus:border-accent-green/30"
              />
            </div>
            {canSelectAll && onSelectAll && filteredOptions.length > 1 && (
              <button
                type="button"
                onClick={() => onSelectAll(filteredOptions)}
                className="mt-2 w-full py-1.5 px-3 rounded-md bg-accent-green/10 border border-accent-green/20 text-[10px] font-bold text-accent-green hover:bg-accent-green/20 transition-all uppercase tracking-wider"
              >
                Select All {searchTerm ? `Filtered (${filteredOptions.length})` : `(${options.length})`}
              </button>
            )}
          </div>

          {/* Options List */}
          <div className="max-h-60 overflow-y-auto scrollbar-thin">
            {filteredOptions.length > 0 ? (
              filteredOptions.map((opt) => (
                <button
                  key={opt[valueKey]}
                  type="button"
                  onClick={() => {
                    onChange(opt[valueKey], opt);
                    setIsOpen(false);
                  }}
                  className={`w-full flex items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-white/5 transition-colors ${
                    String(value) === String(opt[valueKey]) ? 'bg-accent-green/5 text-accent-green font-semibold' : 'text-text-secondary'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    {opt[iconKey] ? (
                      <img src={opt[iconKey]} alt="" className="w-4 h-4 object-contain shrink-0" />
                    ) : (
                      <Globe className="w-3.5 h-3.5 text-text-muted shrink-0" />
                    )}
                    <span className="truncate">{opt[labelKey]}</span>
                    {opt.area && (
                       <span className="text-[10px] opacity-40 truncate">· {opt.area}</span>
                    )}
                  </div>
                  {String(value) === String(opt[valueKey]) && <Check className="w-3.5 h-3.5" />}
                </button>
              ))
            ) : loading ? (
              <div className="p-8 flex flex-col items-center justify-center gap-3">
                <Spinner className="w-6 h-6 text-accent-green" />
                <span className="text-xs text-text-muted animate-pulse font-medium">Fetching data...</span>
              </div>
            ) : (
              <div className="p-4 text-center text-xs text-text-muted italic">
                {emptyMessage}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Spinner({ className }) {
  return (
    <svg className={`animate-spin ${className}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
  );
}
