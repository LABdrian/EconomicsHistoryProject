import React, { useState, useEffect, useRef } from 'react';
import { Search, Filter, Calendar, Globe, Music, Users, Clock, Zap } from 'lucide-react';

const API_BASE_URL = '/api';

function App() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [filters, setFilters] = useState({
    filter: '',
    year: '',
    country: '',
    source: ''
  });
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchInputRef = useRef(null);

  // Load stats on component mount
  useEffect(() => {
    loadStats();
  }, []);

  // Load autocomplete suggestions
  useEffect(() => {
    if (searchQuery.length >= 2) {
      fetchSuggestions(searchQuery);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  }, [searchQuery]);

  const loadStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/stats`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const fetchSuggestions = async (query) => {
    try {
      const response = await fetch(`${API_BASE_URL}/bands/autocomplete?q=${encodeURIComponent(query)}&limit=5`);
      const data = await response.json();
      setSuggestions(data.suggestions || []);
      setShowSuggestions(true);
    } catch (error) {
      console.error('Error fetching suggestions:', error);
    }
  };

  const handleSearch = async (query = searchQuery) => {
    if (!query.trim()) return;
    
    setLoading(true);
    setShowSuggestions(false);
    
    try {
      const params = new URLSearchParams({
        q: query,
        limit: '20'
      });
      
      // Add filters
      Object.entries(filters).forEach(([key, value]) => {
        if (value) {
          params.append(key, value);
        }
      });
      
      const response = await fetch(`${API_BASE_URL}/search?${params}`);
      const data = await response.json();
      
      if (response.ok) {
        setSearchResults(data.hits || []);
      } else {
        console.error('Search error:', data.detail);
        setSearchResults([]);
      }
    } catch (error) {
      console.error('Error searching:', error);
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setSearchQuery(suggestion.band);
    setShowSuggestions(false);
    handleSearch(suggestion.band);
  };

  const handleFilterChange = (key, value) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    
    // Auto-search if there's a query
    if (searchQuery.trim()) {
      setTimeout(() => handleSearch(), 100);
    }
  };

  const clearFilters = () => {
    setFilters({
      filter: '',
      year: '',
      country: '',
      source: ''
    });
    if (searchQuery.trim()) {
      setTimeout(() => handleSearch(), 100);
    }
  };

  const formatYear = (yearStart, yearEnd) => {
    if (yearStart && yearEnd) {
      return `${yearStart} - ${yearEnd}`;
    } else if (yearStart) {
      return `${yearStart} - present`;
    }
    return 'Unknown';
  };

  const getSourceColor = (source) => {
    const colors = {
      musicbrainz: 'bg-blue-100 text-blue-800',
      theaudiodb: 'bg-green-100 text-green-800',
      discogs: 'bg-purple-100 text-purple-800'
    };
    return colors[source] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900">
      {/* Header */}
      <header className="bg-black/20 backdrop-blur-sm border-b border-gray-700">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Zap className="h-8 w-8 text-purple-400" />
              <h1 className="text-3xl font-bold text-white">
                PostPunk Archive
              </h1>
              <span className="text-purple-300 text-sm font-medium">1980-1999</span>
            </div>
            {stats && (
              <div className="text-right text-gray-300">
                <div className="text-sm">
                  {stats.total_documents.toLocaleString()} records indexed
                </div>
                {stats.is_indexing && (
                  <div className="text-xs text-yellow-400">
                    ⚡ Indexing...
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Search Section */}
        <div className="max-w-4xl mx-auto mb-8">
          <div className="relative">
            <div className="relative">
              <Search className="absolute left-4 top-4 h-5 w-5 text-gray-400" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search bands, albums, tracks, or members..."
                className="w-full pl-12 pr-4 py-4 text-lg bg-white/10 backdrop-blur-sm border border-gray-600 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
              <button
                onClick={() => handleSearch()}
                disabled={loading}
                className="absolute right-2 top-2 px-6 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 text-white rounded-lg transition-colors"
              >
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>

            {/* Autocomplete Suggestions */}
            {showSuggestions && suggestions.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-white/95 backdrop-blur-sm border border-gray-300 rounded-lg shadow-lg z-10">
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="w-full px-4 py-3 text-left hover:bg-purple-50 border-b border-gray-200 last:border-b-0 first:rounded-t-lg last:rounded-b-lg"
                  >
                    <div className="font-medium text-gray-900">{suggestion.band}</div>
                    <div className="text-sm text-gray-600">
                      {suggestion.country && `${suggestion.country} • `}
                      {suggestion.year_start && `Since ${suggestion.year_start}`}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Filters */}
          <div className="mt-6 flex flex-wrap gap-4">
            <select
              value={filters.filter}
              onChange={(e) => handleFilterChange('filter', e.target.value)}
              className="px-4 py-2 bg-white/10 backdrop-blur-sm border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="">All Types</option>
              <option value="band">Bands Only</option>
              <option value="album">Albums Only</option>
              <option value="track">Tracks Only</option>
            </select>

            <input
              type="number"
              placeholder="Year"
              min="1980"
              max="1999"
              value={filters.year}
              onChange={(e) => handleFilterChange('year', e.target.value)}
              className="px-4 py-2 bg-white/10 backdrop-blur-sm border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
            />

            <input
              type="text"
              placeholder="Country"
              value={filters.country}
              onChange={(e) => handleFilterChange('country', e.target.value)}
              className="px-4 py-2 bg-white/10 backdrop-blur-sm border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
            />

            <select
              value={filters.source}
              onChange={(e) => handleFilterChange('source', e.target.value)}
              className="px-4 py-2 bg-white/10 backdrop-blur-sm border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="">All Sources</option>
              <option value="musicbrainz">MusicBrainz</option>
              <option value="theaudiodb">TheAudioDB</option>
              <option value="discogs">Discogs</option>
            </select>

            {Object.values(filters).some(f => f) && (
              <button
                onClick={clearFilters}
                className="px-4 py-2 bg-red-600/20 border border-red-500 rounded-lg text-red-300 hover:bg-red-600/30 transition-colors"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>

        {/* Results */}
        <div className="max-w-6xl mx-auto">
          {loading && (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto"></div>
              <p className="text-gray-400 mt-4">Searching the post-punk archives...</p>
            </div>
          )}

          {!loading && searchResults.length > 0 && (
            <div className="space-y-4">
              <div className="text-gray-300 mb-4">
                Found {searchResults.length} results
              </div>
              {searchResults.map((result, index) => (
                <div
                  key={result.id || index}
                  className="bg-white/10 backdrop-blur-sm border border-gray-600 rounded-xl p-6 hover:bg-white/15 transition-colors"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-white mb-2">
                        {result.band}
                      </h3>
                      
                      <div className="flex flex-wrap gap-4 text-sm text-gray-300 mb-3">
                        {result.country && (
                          <div className="flex items-center gap-1">
                            <Globe className="h-4 w-4" />
                            {result.country}
                          </div>
                        )}
                        
                        {(result.year_start || result.year_end) && (
                          <div className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            {formatYear(result.year_start, result.year_end)}
                          </div>
                        )}
                        
                        {result.album && (
                          <div className="flex items-center gap-1">
                            <Music className="h-4 w-4" />
                            {result.album}
                            {result.release_date && ` (${result.release_date})`}
                          </div>
                        )}
                        
                        {result.member && (
                          <div className="flex items-center gap-1">
                            <Users className="h-4 w-4" />
                            {result.member}
                            {result.role && ` - ${result.role}`}
                          </div>
                        )}
                      </div>
                      
                      {result.description && (
                        <p className="text-gray-400 text-sm mb-3 line-clamp-3">
                          {result.description}
                        </p>
                      )}
                    </div>
                    
                    <div className="ml-4 flex flex-col items-end gap-2">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getSourceColor(result.source)}`}>
                        {result.source}
                      </span>
                      
                      {result.hit_rank > 0 && (
                        <span className="bg-yellow-500/20 text-yellow-300 px-2 py-1 rounded-full text-xs">
                          #{result.hit_rank} Hit
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {!loading && searchQuery && searchResults.length === 0 && (
            <div className="text-center py-12">
              <Music className="h-16 w-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-medium text-gray-300 mb-2">No results found</h3>
              <p className="text-gray-500">
                Try adjusting your search query or filters
              </p>
            </div>
          )}

          {!loading && !searchQuery && (
            <div className="text-center py-12">
              <Zap className="h-16 w-16 text-purple-400 mx-auto mb-4" />
              <h3 className="text-xl font-medium text-gray-300 mb-2">
                Explore the Post-Punk Universe
              </h3>
              <p className="text-gray-500 mb-6">
                Search through bands, albums, and tracks from the golden era of post-punk (1980-1999)
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {['Joy Division', 'The Cure', 'Bauhaus', 'Siouxsie and the Banshees', 'Gang of Four'].map(band => (
                  <button
                    key={band}
                    onClick={() => {
                      setSearchQuery(band);
                      handleSearch(band);
                    }}
                    className="px-4 py-2 bg-purple-600/20 border border-purple-500 rounded-lg text-purple-300 hover:bg-purple-600/30 transition-colors text-sm"
                  >
                    {band}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-black/20 backdrop-blur-sm border-t border-gray-700 mt-16">
        <div className="container mx-auto px-4 py-8">
          <div className="text-center text-gray-400">
            <p className="mb-2">
              PostPunk Archive - Exploring the post-punk movement through open data
            </p>
            <p className="text-sm">
              Data sources: MusicBrainz, TheAudioDB, Discogs | 
              <a href="/api/docs" className="text-purple-400 hover:text-purple-300 ml-2">
                API Documentation
              </a>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;