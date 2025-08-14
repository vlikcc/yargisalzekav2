import { useState } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Textarea } from '@/components/ui/textarea.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { ScrollArea } from '@/components/ui/scroll-area.jsx'
import { 
  FileText, 
  Download, 
  Copy, 
  Wand2, 
  CheckCircle,
  AlertCircle,
  Loader2,
  Plus,
  X
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth.jsx'
import { apiService, ApiError } from '../services/api.js'

const PetitionGenerator = ({ caseText, selectedDecisions = [] }) => {
  const [petitionText, setPetitionText] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [customDecisions, setCustomDecisions] = useState([])
  const [newDecisionText, setNewDecisionText] = useState('')

  const { getAuthHeaders } = useAuth()

  const handleGeneratePetition = async () => {
    if (!caseText.trim()) {
      setError('Olay metni gereklidir')
      return
    }

    try {
      setIsGenerating(true)
      setError('')
      setSuccess('')
      
      const allDecisions = [...selectedDecisions, ...customDecisions]
      
      const response = await apiService.post('/ai/generate-petition', {
        case_text: caseText,
        relevant_decisions: allDecisions
      }, getAuthHeaders())
      
      if (response.success) {
        setPetitionText(response.petition_template)
        setSuccess('Dilekçe şablonu başarıyla oluşturuldu!')
      } else {
        setError(response.message || 'Dilekçe oluşturulamadı')
      }
    } catch (error) {
      console.error('Petition generation error:', error)
      
      if (error instanceof ApiError) {
        if (error.status === 403) {
          setError('Dilekçe oluşturma özelliği premium pakette mevcuttur. Lütfen aboneliğinizi yükseltin.')
        } else {
          setError(error.getUserMessage())
        }
      } else {
        setError('Dilekçe oluşturulurken bir hata oluştu')
      }
    } finally {
      setIsGenerating(false)
    }
  }

  const handleCopyPetition = async () => {
    try {
      await navigator.clipboard.writeText(petitionText)
      setSuccess('Dilekçe panoya kopyalandı!')
      setTimeout(() => setSuccess(''), 3000)
    } catch (error) {
      setError('Kopyalama sırasında bir hata oluştu')
    }
  }

  const handleDownloadPetition = () => {
    const element = document.createElement('a')
    const file = new Blob([petitionText], { type: 'text/plain' })
    element.href = URL.createObjectURL(file)
    element.download = `dilekce-${new Date().toISOString().split('T')[0]}.txt`
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
    
    setSuccess('Dilekçe indirildi!')
    setTimeout(() => setSuccess(''), 3000)
  }

  const handleAddCustomDecision = () => {
    if (newDecisionText.trim()) {
      setCustomDecisions(prev => [...prev, {
        id: `custom-${Date.now()}`,
        title: `Özel Karar ${customDecisions.length + 1}`,
        content: newDecisionText.trim(),
        custom: true
      }])
      setNewDecisionText('')
    }
  }

  const handleRemoveCustomDecision = (decisionId) => {
    setCustomDecisions(prev => prev.filter(decision => decision.id !== decisionId))
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="bg-gray-900/95 border-gray-700">
        <CardHeader>
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-yellow-600 rounded-full">
              <FileText className="h-6 w-6 text-black" />
            </div>
            <div>
              <CardTitle className="text-xl text-white">Dilekçe Oluşturucu</CardTitle>
              <CardDescription className="text-gray-300">
                AI destekli dilekçe şablonu oluşturun
              </CardDescription>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Selected Decisions */}
      {(selectedDecisions.length > 0 || customDecisions.length > 0) && (
        <Card className="bg-gray-900/95 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white">Seçili Kararlar</CardTitle>
            <CardDescription className="text-gray-300">
              Dilekçede referans olarak kullanılacak kararlar
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {selectedDecisions.map((decision, index) => (
                <div key={decision.id || index} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-md">
                  <div>
                    <p className="text-white font-medium">{decision.title}</p>
                    <p className="text-gray-400 text-sm">{decision.court} - {decision.date}</p>
                  </div>
                  <Badge className="bg-blue-600 text-white">Seçili</Badge>
                </div>
              ))}
              
              {customDecisions.map((decision) => (
                <div key={decision.id} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-md">
                  <div className="flex-1">
                    <p className="text-white font-medium">{decision.title}</p>
                    <p className="text-gray-400 text-sm">{decision.content.substring(0, 100)}...</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge className="bg-green-600 text-white">Özel</Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveCustomDecision(decision.id)}
                      className="text-red-400 hover:text-red-300"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add Custom Decision */}
      <Card className="bg-gray-900/95 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Özel Karar Ekle</CardTitle>
          <CardDescription className="text-gray-300">
            Kendi bulduğunuz kararları da dilekçeye dahil edebilirsiniz
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="Karar metnini buraya yapıştırın..."
            value={newDecisionText}
            onChange={(e) => setNewDecisionText(e.target.value)}
            rows={4}
            className="bg-white/10 border-white/20 text-white placeholder:text-gray-400"
          />
          <Button
            onClick={handleAddCustomDecision}
            disabled={!newDecisionText.trim()}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            <Plus className="mr-2 h-4 w-4" />
            Karar Ekle
          </Button>
        </CardContent>
      </Card>

      {/* Generate Button */}
      <Card className="bg-gray-900/95 border-gray-700">
        <CardContent className="p-6">
          <Button
            onClick={handleGeneratePetition}
            disabled={isGenerating || !caseText.trim()}
            className="w-full btn-primary"
            size="lg"
          >
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Dilekçe Oluşturuluyor...
              </>
            ) : (
              <>
                <Wand2 className="mr-2 h-4 w-4" />
                Dilekçe Oluştur
              </>
            )}
          </Button>

          {error && (
            <div className="mt-4 bg-red-500/20 border border-red-500/30 rounded-md p-3 flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 text-red-400" />
              <span className="text-red-200 text-sm">{error}</span>
            </div>
          )}

          {success && (
            <div className="mt-4 bg-green-500/20 border border-green-500/30 rounded-md p-3 flex items-center space-x-2">
              <CheckCircle className="h-4 w-4 text-green-400" />
              <span className="text-green-200 text-sm">{success}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Generated Petition */}
      {petitionText && (
        <Card className="bg-gray-900/95 border-gray-700">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-white">Oluşturulan Dilekçe</CardTitle>
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopyPetition}
                  className="border-gray-600 text-gray-300 hover:bg-gray-800"
                >
                  <Copy className="mr-2 h-4 w-4" />
                  Kopyala
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownloadPetition}
                  className="border-gray-600 text-gray-300 hover:bg-gray-800"
                >
                  <Download className="mr-2 h-4 w-4" />
                  İndir
                </Button>
              </div>
            </div>
            <CardDescription className="text-gray-300">
              AI tarafından oluşturulan dilekçe şablonu
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-96 w-full rounded-md border border-gray-700 p-4">
              <div className="text-gray-300 leading-relaxed whitespace-pre-wrap">
                {petitionText}
              </div>
            </ScrollArea>
            <div className="mt-4 p-3 bg-yellow-500/20 border border-yellow-500/30 rounded-md">
              <p className="text-yellow-200 text-sm">
                <strong>Uyarı:</strong> Bu dilekçe şablonu AI tarafından oluşturulmuştur. 
                Kullanmadan önce mutlaka bir hukuk uzmanı tarafından gözden geçirilmelidir.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default PetitionGenerator

