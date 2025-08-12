import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { ScrollArea } from '@/components/ui/scroll-area.jsx'
import { 
  History, 
  Search, 
  Calendar, 
  Clock, 
  Trash2,
  Eye,
  RefreshCw,
  AlertCircle
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth.js'
import { apiService, ApiError } from '../services/api.js'

const SearchHistory = ({ onSelectSearch }) => {
  const [searchHistory, setSearchHistory] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const { getAuthHeaders } = useAuth()

  useEffect(() => {
    fetchSearchHistory()
  }, [])

  const fetchSearchHistory = async () => {
    try {
      setIsLoading(true)
      setError('')
      
      const response = await apiService.get('/user/search-history', getAuthHeaders())
      
      if (response.success) {
        setSearchHistory(response.data || [])
      } else {
        setError(response.message || 'Arama geçmişi alınamadı')
      }
    } catch (error) {
      console.error('Search history error:', error)
      
      if (error instanceof ApiError) {
        setError(error.getUserMessage())
      } else {
        setError('Arama geçmişi alınırken bir hata oluştu')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteSearch = async (searchId) => {
    try {
      const response = await apiService.delete(`/user/search-history/${searchId}`, getAuthHeaders())
      
      if (response.success) {
        setSearchHistory(prev => prev.filter(search => search.id !== searchId))
      } else {
        setError(response.message || 'Arama silinemedi')
      }
    } catch (error) {
      console.error('Delete search error:', error)
      setError('Arama silinirken bir hata oluştu')
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Belirtilmemiş'
    try {
      return new Date(dateString).toLocaleDateString('tr-TR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateString
    }
  }

  const truncateText = (text, maxLength = 100) => {
    if (!text) return ''
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
  }

  if (isLoading) {
    return (
      <Card className="bg-gray-900/95 border-gray-700">
        <CardContent className="p-6 text-center">
          <RefreshCw className="h-8 w-8 animate-spin text-yellow-400 mx-auto mb-4" />
          <p className="text-gray-300">Arama geçmişi yükleniyor...</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-gray-900/95 border-gray-700">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <History className="h-5 w-5 text-yellow-400" />
            <CardTitle className="text-white">Arama Geçmişi</CardTitle>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchSearchHistory}
            className="text-gray-400 hover:text-white"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
        <CardDescription className="text-gray-300">
          Son aramalarınız ve sonuçları
        </CardDescription>
      </CardHeader>

      <CardContent>
        {error && (
          <div className="mb-4 bg-red-500/20 border border-red-500/30 rounded-md p-3 flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 text-red-400" />
            <span className="text-red-200 text-sm">{error}</span>
          </div>
        )}

        {searchHistory.length === 0 ? (
          <div className="text-center py-8">
            <Search className="h-12 w-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">Henüz arama yapmadınız</p>
            <p className="text-gray-500 text-sm mt-2">
              İlk aramanızı yapın ve geçmişiniz burada görünecek
            </p>
          </div>
        ) : (
          <ScrollArea className="h-96">
            <div className="space-y-3">
              {searchHistory.map((search, index) => (
                <Card key={search.id || index} className="bg-gray-800/50 border-gray-600 hover:border-yellow-400/50 transition-all">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <Calendar className="h-4 w-4 text-gray-400" />
                          <span className="text-sm text-gray-400">
                            {formatDate(search.created_at)}
                          </span>
                          {search.results_count && (
                            <Badge variant="secondary" className="bg-yellow-600/20 text-yellow-300">
                              {search.results_count} sonuç
                            </Badge>
                          )}
                        </div>
                        <p className="text-white text-sm font-medium mb-2">
                          {truncateText(search.case_text)}
                        </p>
                        {search.keywords && search.keywords.length > 0 && (
                          <div className="flex flex-wrap gap-1 mb-2">
                            {search.keywords.slice(0, 3).map((keyword, idx) => (
                              <Badge key={idx} variant="outline" className="text-xs border-gray-600 text-gray-300">
                                {keyword}
                              </Badge>
                            ))}
                            {search.keywords.length > 3 && (
                              <Badge variant="outline" className="text-xs border-gray-600 text-gray-300">
                                +{search.keywords.length - 3}
                              </Badge>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="flex space-x-1 ml-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onSelectSearch && onSelectSearch(search)}
                          className="text-gray-400 hover:text-yellow-400"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteSearch(search.id)}
                          className="text-gray-400 hover:text-red-400"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    
                    {search.ai_score && (
                      <div className="flex items-center space-x-2 text-xs">
                        <span className="text-gray-400">En yüksek skor:</span>
                        <Badge className={`${search.ai_score > 70 ? "bg-green-600" : search.ai_score > 40 ? "bg-yellow-600 text-black" : "bg-gray-600"}`}>
                          {search.ai_score}/100
                        </Badge>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  )
}

export default SearchHistory

