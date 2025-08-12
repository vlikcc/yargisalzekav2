import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Separator } from '@/components/ui/separator.jsx'
import { ScrollArea } from '@/components/ui/scroll-area.jsx'
import { 
  FileText, 
  Download, 
  Calendar, 
  Scale, 
  Hash, 
  Eye,
  X,
  AlertCircle,
  CheckCircle,
  Loader2
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth.js'
import { apiService, ApiError } from '../services/api.js'

const DecisionDetailModal = ({ isOpen, onClose, decisionId, decisionTitle }) => {
  const [decisionData, setDecisionData] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [isExporting, setIsExporting] = useState(false)

  const { getAuthHeaders } = useAuth()

  useEffect(() => {
    if (isOpen && decisionId) {
      fetchDecisionDetail()
    }
  }, [isOpen, decisionId])

  const fetchDecisionDetail = async () => {
    try {
      setIsLoading(true)
      setError('')
      
      const response = await apiService.get(`/decisions/${decisionId}`, getAuthHeaders())
      
      if (response.success) {
        setDecisionData(response.decision)
      } else {
        setError(response.message || 'Karar detayı alınamadı')
      }
    } catch (error) {
      console.error('Decision detail error:', error)
      
      if (error instanceof ApiError) {
        if (error.status === 403) {
          setError('Bu özellik premium pakette mevcuttur. Lütfen aboneliğinizi yükseltin.')
        } else {
          setError(error.getUserMessage())
        }
      } else {
        setError('Karar detayı alınırken bir hata oluştu')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleExportPDF = async () => {
    try {
      setIsExporting(true)
      
      const response = await apiService.post(`/decisions/${decisionId}/export-pdf`, {}, getAuthHeaders())
      
      if (response.success) {
        // PDF download link'ini aç
        const link = document.createElement('a')
        link.href = response.pdf_url
        link.download = `yargitay-karari-${decisionId}.pdf`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      } else {
        setError(response.message || 'PDF export edilemedi')
      }
    } catch (error) {
      console.error('PDF export error:', error)
      
      if (error instanceof ApiError) {
        if (error.status === 403) {
          setError('PDF export özelliği premium pakette mevcuttur.')
        } else {
          setError(error.getUserMessage())
        }
      } else {
        setError('PDF export sırasında bir hata oluştu')
      }
    } finally {
      setIsExporting(false)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Belirtilmemiş'
    try {
      return new Date(dateString).toLocaleDateString('tr-TR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    } catch {
      return dateString
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-4xl bg-gray-900/95 border-gray-700 max-h-[90vh] overflow-hidden">
        <CardHeader className="relative border-b border-gray-700">
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="absolute right-2 top-2 text-gray-400 hover:text-white"
          >
            <X className="h-4 w-4" />
          </Button>
          
          <div className="flex items-start space-x-3 pr-8">
            <div className="p-2 bg-yellow-600 rounded-full">
              <FileText className="h-6 w-6 text-black" />
            </div>
            <div className="flex-1">
              <CardTitle className="text-xl text-white">
                {decisionTitle || 'Yargıtay Kararı Detayı'}
              </CardTitle>
              <CardDescription className="text-gray-300">
                Karar ID: {decisionId}
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {isLoading && (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="h-8 w-8 animate-spin text-yellow-400" />
              <span className="ml-3 text-gray-300">Karar detayı yükleniyor...</span>
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-red-500/20 border border-red-500/30 rounded-md p-4 flex items-center space-x-3">
                <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
                <span className="text-red-200">{error}</span>
              </div>
            </div>
          )}

          {decisionData && !isLoading && (
            <div className="flex flex-col h-full">
              {/* Decision Info */}
              <div className="p-6 border-b border-gray-700">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Scale className="h-4 w-4 text-yellow-400" />
                      <span className="text-sm text-gray-400">Mahkeme:</span>
                    </div>
                    <p className="text-white font-medium">{decisionData.court}</p>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Calendar className="h-4 w-4 text-yellow-400" />
                      <span className="text-sm text-gray-400">Karar Tarihi:</span>
                    </div>
                    <p className="text-white font-medium">{formatDate(decisionData.date)}</p>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Hash className="h-4 w-4 text-yellow-400" />
                      <span className="text-sm text-gray-400">Esas No:</span>
                    </div>
                    <p className="text-white font-medium">{decisionData.case_number}</p>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Hash className="h-4 w-4 text-yellow-400" />
                      <span className="text-sm text-gray-400">Karar No:</span>
                    </div>
                    <p className="text-white font-medium">{decisionData.decision_number}</p>
                  </div>
                </div>

                {/* Keywords */}
                {decisionData.keywords && decisionData.keywords.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-sm text-gray-400">Anahtar Kelimeler:</span>
                    <div className="flex flex-wrap gap-2">
                      {decisionData.keywords.map((keyword, index) => (
                        <Badge key={index} variant="secondary" className="bg-yellow-600/20 text-yellow-300">
                          {keyword}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Summary */}
              {decisionData.summary && (
                <div className="p-6 border-b border-gray-700">
                  <h3 className="text-lg font-semibold text-white mb-3">Özet</h3>
                  <p className="text-gray-300 leading-relaxed">{decisionData.summary}</p>
                </div>
              )}

              {/* Full Text */}
              <div className="flex-1 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white">Karar Metni</h3>
                  <Button
                    onClick={handleExportPDF}
                    disabled={isExporting}
                    className="bg-yellow-600 hover:bg-yellow-700 text-black"
                  >
                    {isExporting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Export Ediliyor...
                      </>
                    ) : (
                      <>
                        <Download className="mr-2 h-4 w-4" />
                        PDF İndir
                      </>
                    )}
                  </Button>
                </div>
                
                <ScrollArea className="h-96 w-full rounded-md border border-gray-700 p-4">
                  <div className="text-gray-300 leading-relaxed whitespace-pre-wrap">
                    {decisionData.full_text}
                  </div>
                </ScrollArea>
              </div>

              {/* Actions */}
              <div className="p-6 border-t border-gray-700">
                <div className="flex justify-end space-x-3">
                  <Button
                    variant="outline"
                    onClick={onClose}
                    className="border-gray-600 text-gray-300 hover:bg-gray-800"
                  >
                    Kapat
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default DecisionDetailModal

