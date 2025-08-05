import { useState } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Textarea } from '@/components/ui/textarea.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { Brain, Search, FileText, Zap, CheckCircle, Star, Clock, Users } from 'lucide-react'
import './App.css'

function App() {
  const [caseText, setCaseText] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [keywords, setKeywords] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('search')

  const handleSmartSearch = async () => {
    if (!caseText.trim()) return
    
    setIsLoading(true)
    setError('')
    try {
      const response = await fetch('/api/v1/ai/smart-search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          case_text: caseText,
          max_results: 10
        })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      if (data.success) {
        setKeywords(data.keywords)
        setSearchResults(data.analyzed_results)
        setError('')
      } else {
        setError(data.message || 'Arama sırasında bir hata oluştu')
      }
    } catch (error) {
      console.error('Arama hatası:', error)
      setError('Sunucuya bağlanırken bir hata oluştu. Lütfen daha sonra tekrar deneyin.')
    } finally {
      setIsLoading(false)
    }
  }

  const subscriptionPlans = [
    {
      name: 'Temel Paket',
      price: '99 TL',
      period: 'aylık',
      searches: '50 arama',
      features: [
        'Anahtar Kelime Çıkarma',
        'AI Destekli Karar Analizi',
        'Temel Destek'
      ],
      popular: false
    },
    {
      name: 'Standart Paket',
      price: '299 TL',
      period: 'aylık',
      searches: '500 arama',
      features: [
        'Anahtar Kelime Çıkarma',
        'AI Destekli Karar Analizi',
        'Dilekçe Şablonu (10 adet/ay)',
        'Öncelikli Destek'
      ],
      popular: true
    },
    {
      name: 'Premium Paket',
      price: '999 TL',
      period: 'aylık',
      searches: 'Sınırsız',
      features: [
        'Anahtar Kelime Çıkarma',
        'AI Destekli Karar Analizi',
        'Sınırsız Dilekçe Şablonu',
        '7/24 Premium Destek',
        'API Erişimi'
      ],
      popular: false
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <Brain className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">YARGISAL ZEKA</h1>
                <p className="text-sm text-gray-600">Yapay Zeka Destekli Yargıtay Kararı Arama Platformu</p>
              </div>
            </div>
            <nav className="flex space-x-8">
              <Button variant="ghost" onClick={() => setActiveTab('search')}>Ana Sayfa</Button>
              <Button variant="ghost" onClick={() => setActiveTab('pricing')}>Fiyatlandırma</Button>
              <Button variant="ghost" onClick={() => setActiveTab('about')}>Hakkında</Button>
              <Button>Giriş Yap</Button>
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="search">Akıllı Arama</TabsTrigger>
            <TabsTrigger value="pricing">Abonelik Planları</TabsTrigger>
            <TabsTrigger value="about">Platform Özellikleri</TabsTrigger>
          </TabsList>

          {/* Akıllı Arama Sekmesi */}
          <TabsContent value="search" className="space-y-6">
            <div className="text-center py-8">
              <h2 className="text-4xl font-bold text-gray-900 mb-4">
                Hukuk Araştırmalarında Devrim
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                Yapay zeka destekli platformumuz ile Yargıtay kararlarını saniyeler içinde bulun, 
                analiz edin ve dilekçelerinize entegre edin.
              </p>
            </div>

            <Card className="max-w-4xl mx-auto">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Search className="h-5 w-5" />
                  <span>Olay Metninizi Girin</span>
                </CardTitle>
                <CardDescription>
                  Hukuki durumunuzu detaylı olarak açıklayın. AI sistemimiz otomatik olarak 
                  anahtar kelimeleri çıkaracak ve en alakalı Yargıtay kararlarını bulacak.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  placeholder="Örnek: Müvekkilim A şirketi ile B şirketi arasında imzalanan satış sözleşmesinde, B şirketi teslim tarihini geçirmesi nedeniyle tazminat talep etmekteyiz..."
                  value={caseText}
                  onChange={(e) => setCaseText(e.target.value)}
                  rows={6}
                  className="w-full"
                />
                <Button 
                  onClick={handleSmartSearch}
                  disabled={!caseText.trim() || isLoading}
                  className="w-full"
                  size="lg"
                >
                  {isLoading ? (
                    <>
                      <Clock className="mr-2 h-4 w-4 animate-spin" />
                      AI Analiz Ediyor...
                    </>
                  ) : (
                    <>
                      <Brain className="mr-2 h-4 w-4" />
                      Akıllı Arama Başlat
                    </>
                  )}
                </Button>
                {error && (
                  <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-red-800 text-sm">{error}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Anahtar Kelimeler */}
            {keywords.length > 0 && (
              <Card className="max-w-4xl mx-auto">
                <CardHeader>
                  <CardTitle>Çıkarılan Anahtar Kelimeler</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {keywords.map((keyword, index) => (
                      <Badge key={index} variant="secondary">
                        {keyword}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Arama Sonuçları */}
            {searchResults.length > 0 && (
              <div className="max-w-4xl mx-auto space-y-4">
                <h3 className="text-2xl font-bold text-gray-900">
                  Bulunan Yargıtay Kararları ({searchResults.length})
                </h3>
                {searchResults.map((result, index) => (
                  <Card key={index} className="hover:shadow-lg transition-shadow">
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <CardTitle className="text-lg">{result.title || `Karar ${index + 1}`}</CardTitle>
                        <div className="flex items-center space-x-2">
                          <Badge variant={result.ai_score > 70 ? "default" : result.ai_score > 40 ? "secondary" : "outline"}>
                            AI Skoru: {result.ai_score}/100
                          </Badge>
                          {result.ai_score > 70 && <Star className="h-4 w-4 text-yellow-500" />}
                        </div>
                      </div>
                      <CardDescription>{result.ai_explanation}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-gray-600 mb-2">
                        <strong>Benzerlik:</strong> {result.ai_similarity}
                      </p>
                      <p className="text-sm text-gray-800 line-clamp-3">
                        {result.content?.substring(0, 300)}...
                      </p>
                      <div className="mt-4 flex space-x-2">
                        <Button size="sm" variant="outline">
                          <FileText className="mr-2 h-4 w-4" />
                          Detayları Gör
                        </Button>
                        <Button size="sm" variant="outline">
                          Dilekçeye Ekle
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Abonelik Planları Sekmesi */}
          <TabsContent value="pricing" className="space-y-6">
            <div className="text-center py-8">
              <h2 className="text-4xl font-bold text-gray-900 mb-4">Abonelik Planları</h2>
              <p className="text-xl text-gray-600">
                İhtiyacınıza uygun planı seçin ve hukuki araştırmalarınızı hızlandırın
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
              {subscriptionPlans.map((plan, index) => (
                <Card key={index} className={`relative ${plan.popular ? 'border-blue-500 shadow-lg scale-105' : ''}`}>
                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                      <Badge className="bg-blue-500">En Popüler</Badge>
                    </div>
                  )}
                  <CardHeader className="text-center">
                    <CardTitle className="text-2xl">{plan.name}</CardTitle>
                    <div className="text-4xl font-bold text-blue-600">
                      {plan.price}
                      <span className="text-lg text-gray-500">/{plan.period}</span>
                    </div>
                    <CardDescription className="text-lg">{plan.searches}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <ul className="space-y-3">
                      {plan.features.map((feature, featureIndex) => (
                        <li key={featureIndex} className="flex items-center space-x-2">
                          <CheckCircle className="h-5 w-5 text-green-500" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                    <Button className="w-full" variant={plan.popular ? "default" : "outline"}>
                      Planı Seç
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Platform Özellikleri Sekmesi */}
          <TabsContent value="about" className="space-y-6">
            <div className="text-center py-8">
              <h2 className="text-4xl font-bold text-gray-900 mb-4">Platform Özellikleri</h2>
              <p className="text-xl text-gray-600">
                Hukuk profesyonellerinin ihtiyaçları için özel olarak tasarlanmış özellikler
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card className="text-center">
                <CardHeader>
                  <Brain className="h-12 w-12 text-blue-600 mx-auto mb-4" />
                  <CardTitle>Yapay Zeka Destekli Analiz</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600">
                    Google Gemini AI ile olay metinlerinden otomatik anahtar kelime çıkarma ve karar analizi
                  </p>
                </CardContent>
              </Card>

              <Card className="text-center">
                <CardHeader>
                  <Zap className="h-12 w-12 text-yellow-600 mx-auto mb-4" />
                  <CardTitle>Paralel Arama Teknolojisi</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600">
                    Çoklu anahtar kelimelerle eş zamanlı arama yaparak sonuçları hızlı bir şekilde getirir
                  </p>
                </CardContent>
              </Card>

              <Card className="text-center">
                <CardHeader>
                  <Star className="h-12 w-12 text-purple-600 mx-auto mb-4" />
                  <CardTitle>Akıllı Puanlama Sistemi</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600">
                    Bulunan kararları olay metniyle ilişkisine göre puanlayarak en alakalı sonuçları öne çıkarır
                  </p>
                </CardContent>
              </Card>

              <Card className="text-center">
                <CardHeader>
                  <FileText className="h-12 w-12 text-green-600 mx-auto mb-4" />
                  <CardTitle>Otomatik Dilekçe Şablonları</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600">
                    Seçilen Yargıtay kararlarını referans alan dilekçe şablonları oluşturur
                  </p>
                </CardContent>
              </Card>
            </div>

            <Card className="max-w-4xl mx-auto">
              <CardHeader>
                <CardTitle>Sistem Çalışma Prensibi</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div className="text-center">
                    <div className="bg-blue-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                      <span className="text-2xl font-bold text-blue-600">1</span>
                    </div>
                    <h4 className="font-semibold mb-2">Olay Analizi</h4>
                    <p className="text-sm text-gray-600">
                      Kullanıcının girdiği olay metni, Google Gemini AI tarafından analiz edilir
                    </p>
                  </div>
                  <div className="text-center">
                    <div className="bg-yellow-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                      <span className="text-2xl font-bold text-yellow-600">2</span>
                    </div>
                    <h4 className="font-semibold mb-2">Paralel Arama</h4>
                    <p className="text-sm text-gray-600">
                      Çıkarılan anahtar kelimeler kullanılarak Yargıtay web sitesinde paralel arama yapılır
                    </p>
                  </div>
                  <div className="text-center">
                    <div className="bg-purple-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                      <span className="text-2xl font-bold text-purple-600">3</span>
                    </div>
                    <h4 className="font-semibold mb-2">Karar Analizi</h4>
                    <p className="text-sm text-gray-600">
                      Bulunan kararlar AI tarafından analiz edilir ve olay metniyle ilişkisine göre puanlanır
                    </p>
                  </div>
                  <div className="text-center">
                    <div className="bg-green-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                      <span className="text-2xl font-bold text-green-600">4</span>
                    </div>
                    <h4 className="font-semibold mb-2">Dilekçe Hazırlama</h4>
                    <p className="text-sm text-gray-600">
                      En alakalı kararlar kullanılarak örnek dilekçe şablonu oluşturulur
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <Brain className="h-6 w-6" />
                <span className="text-xl font-bold">YARGISAL ZEKA</span>
              </div>
              <p className="text-gray-400">
                Hukuk araştırmalarında devrim niteliğinde bir adım
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">İletişim</h4>
              <div className="space-y-2 text-gray-400">
                <p>info@yargisalzeka.com</p>
                <p>+90 (212) 555 1234</p>
                <p>Levent, İstanbul</p>
              </div>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Hızlı Linkler</h4>
              <div className="space-y-2">
                <a href="#" className="block text-gray-400 hover:text-white">Hakkımızda</a>
                <a href="#" className="block text-gray-400 hover:text-white">Fiyatlandırma</a>
                <a href="#" className="block text-gray-400 hover:text-white">Destek</a>
                <a href="#" className="block text-gray-400 hover:text-white">API Dokümantasyonu</a>
              </div>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Ücretsiz Demo</h4>
              <p className="text-gray-400 mb-4">
                Platformumuzu ücretsiz olarak deneyin
              </p>
              <Button className="w-full">Demo İste</Button>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2024 Yargısal Zeka. Tüm hakları saklıdır.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App

