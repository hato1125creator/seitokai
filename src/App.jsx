import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Calendar, Users, FileText, Home, Activity, Bell, Upload, ChevronRight, School, Heart, Star, Filter, RefreshCw } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { getActivities, getAnnouncements, submitFile, sortByDate, filterByCategory, sortAnnouncementsByImportance } from './services/api.js'
import schoolBuilding from './assets/school-building.jpg'
import schoolEvent from './assets/school-event.jpg'
import festival from './assets/festival.jpg'
import './App.css'

// ナビゲーションコンポーネント
function Navigation() {
  const location = useLocation()
  const [isScrolled, setIsScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const navItems = [
    { path: '/', label: 'ホーム', icon: Home },
    { path: '/activities', label: '活動報告', icon: Activity },
    { path: '/announcements', label: 'お知らせ', icon: Bell },
    { path: '/submissions', label: '提出物', icon: Upload }
  ]

  return (
    <motion.nav 
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled ? 'bg-blue-600/95 backdrop-blur-sm shadow-lg' : 'bg-blue-600'
      }`}
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center space-x-3">
            <School className="h-8 w-8 text-white" />
            <span className="text-white font-bold text-lg">千葉英和高校生徒会</span>
          </Link>
          
          <div className="hidden md:flex space-x-8">
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${
                    location.pathname === item.path
                      ? 'bg-blue-700 text-white'
                      : 'text-blue-100 hover:bg-blue-700 hover:text-white'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              )
            })}
          </div>
        </div>
      </div>
    </motion.nav>
  )
}

// ホームページコンポーネント
function HomePage() {
  const [latestNews, setLatestNews] = useState([])
  const [announcements, setAnnouncements] = useState([])
  const [loading, setLoading] = useState(true)

  // データを取得する関数
  const fetchData = async () => {
    setLoading(true)
    try {
      const [activitiesData, announcementsData] = await Promise.all([
        getActivities(),
        getAnnouncements()
      ])

      // 活動報告データを変換（最新3件）
      const formattedActivities = sortByDate(activitiesData, '日付', false)
        .slice(0, 3)
        .map(activity => ({
          id: activity.ID,
          title: activity.タイトル,
          date: activity.日付,
          category: activity.カテゴリー,
          excerpt: activity.内容,
          image: getImageForActivity(activity.カテゴリー)
        }))

      // お知らせデータを変換（最新3件、重要度順）
      const formattedAnnouncements = sortAnnouncementsByImportance(announcementsData)
        .slice(0, 3)
        .map(announcement => ({
          id: announcement.ID,
          title: announcement.タイトル,
          date: announcement.日付,
          category: announcement.カテゴリー,
          important: announcement.重要
        }))

      setLatestNews(formattedActivities)
      setAnnouncements(formattedAnnouncements)
    } catch (error) {
      console.error('データの取得に失敗しました:', error)
    } finally {
      setLoading(false)
    }
  }

  // カテゴリーに応じた画像を取得する関数
  const getImageForActivity = (category) => {
    switch (category) {
      case '行事':
      case '文化祭':
        return festival
      case 'ボランティア':
      case '地域交流':
        return schoolEvent
      default:
        return schoolBuilding
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  return (
    <div className="min-h-screen">
      {/* ヒーローセクション */}
      <motion.section 
        className="relative h-screen flex items-center justify-center bg-gradient-to-br from-blue-600 to-blue-800 overflow-hidden"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1 }}
      >
        <div 
          className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-30"
          style={{ backgroundImage: `url(${schoolBuilding})` }}
        />
        <div className="relative z-10 text-center text-white px-4">
          <motion.h1 
            className="text-5xl md:text-7xl font-bold mb-6"
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.8 }}
          >
            千葉英和高校生徒会
          </motion.h1>
          <motion.p 
            className="text-xl md:text-2xl mb-8 font-light"
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.7, duration: 0.8 }}
          >
            Student Council of Chiba Eiwa High School
          </motion.p>
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.9, duration: 0.8 }}
          >
            <Button size="lg" className="bg-white text-blue-600 hover:bg-blue-50 font-semibold px-8 py-3">
              活動を見る
              <ChevronRight className="ml-2 h-5 w-5" />
            </Button>
          </motion.div>
        </div>
      </motion.section>

      {/* 生徒会とは */}
      <section className="py-20 bg-gradient-to-b from-blue-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            className="text-center mb-16"
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            <h2 className="text-4xl font-bold text-gray-900 mb-6">生徒会とは</h2>
            <p className="text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed">
              生徒の自治活動を推進し、学校生活の向上を目指す組織です。
              生徒の意見を集約し、学校行事の企画・運営、地域との交流など、様々な活動を行っています。
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Calendar,
                title: '企画・運営',
                description: '学校行事の企画・運営',
                color: 'bg-blue-500'
              },
              {
                icon: Users,
                title: '意見集約',
                description: '生徒の声を届ける',
                color: 'bg-green-500'
              },
              {
                icon: Heart,
                title: '地域交流',
                description: '地域との連携活動',
                color: 'bg-purple-500'
              }
            ].map((item, index) => {
              const Icon = item.icon
              return (
                <motion.div
                  key={index}
                  initial={{ y: 50, opacity: 0 }}
                  whileInView={{ y: 0, opacity: 1 }}
                  transition={{ delay: index * 0.2, duration: 0.8 }}
                  viewport={{ once: true }}
                  whileHover={{ y: -10 }}
                  className="bg-white rounded-xl shadow-lg p-8 text-center hover:shadow-xl transition-all duration-300"
                >
                  <div className={`${item.color} w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6`}>
                    <Icon className="h-8 w-8 text-white" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-4">{item.title}</h3>
                  <p className="text-gray-600">{item.description}</p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* 最新の活動報告 */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            className="flex justify-between items-center mb-12"
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl font-bold text-gray-900">最新の活動報告</h2>
            <Link to="/activities">
              <Button variant="outline" className="flex items-center">
                すべて見る
                <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {latestNews.map((news, index) => (
              <motion.div
                key={news.id}
                initial={{ y: 50, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                transition={{ delay: index * 0.2, duration: 0.8 }}
                viewport={{ once: true }}
                whileHover={{ y: -5 }}
              >
                <Card className="overflow-hidden hover:shadow-lg transition-all duration-300">
                  <div className="aspect-video overflow-hidden">
                    <img 
                      src={news.image} 
                      alt={news.title}
                      className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                    />
                  </div>
                  <CardHeader>
                    <div className="flex justify-between items-start mb-2">
                      <Badge variant="secondary">{news.category}</Badge>
                      <span className="text-sm text-gray-500">{news.date}</span>
                    </div>
                    <CardTitle className="text-lg">{news.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription>{news.excerpt}</CardDescription>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* お知らせ */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            className="flex justify-between items-center mb-12"
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl font-bold text-gray-900">お知らせ</h2>
            <Link to="/announcements">
              <Button variant="outline" className="flex items-center">
                すべて見る
                <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </motion.div>

          <motion.div 
            className="bg-white rounded-lg shadow-md overflow-hidden"
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            {announcements.map((announcement, index) => (
              <motion.div
                key={announcement.id}
                className={`p-6 border-b border-gray-200 last:border-b-0 hover:bg-gray-50 transition-colors duration-200 ${
                  announcement.important ? 'bg-red-50 border-l-4 border-l-red-500' : ''
                }`}
                initial={{ x: -50, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1 }}
                transition={{ delay: index * 0.1, duration: 0.5 }}
                viewport={{ once: true }}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <Badge 
                        variant={announcement.important ? "destructive" : "secondary"}
                        className="text-xs"
                      >
                        {announcement.category}
                      </Badge>
                      {announcement.important && (
                        <Star className="h-4 w-4 text-red-500 fill-current" />
                      )}
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">
                      {announcement.title}
                    </h3>
                  </div>
                  <span className="text-sm text-gray-500 ml-4">{announcement.date}</span>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* 生徒会役員紹介 */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            className="text-center mb-16"
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl font-bold text-gray-900 mb-6">生徒会役員紹介</h2>
            <p className="text-lg text-gray-600">
              生徒の皆さんのために活動している生徒会役員をご紹介します
            </p>
          </motion.div>

          <div className="grid md:grid-cols-4 gap-8">
            {[
              { position: '会長', name: '山田 太郎' },
              { position: '副会長', name: '佐藤 花子' },
              { position: '書記', name: '田中 次郎' },
              { position: '会計', name: '鈴木 美咲' }
            ].map((member, index) => (
              <motion.div
                key={index}
                initial={{ y: 50, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                transition={{ delay: index * 0.2, duration: 0.8 }}
                viewport={{ once: true }}
                whileHover={{ y: -5 }}
                className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-all duration-300"
              >
                <div className="aspect-square bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center">
                  <Users className="h-16 w-16 text-white" />
                </div>
                <div className="p-6 text-center">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">{member.position}</h3>
                  <p className="text-gray-600">{member.name}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

// 活動報告ページ
function ActivitiesPage() {
  const [activities, setActivities] = useState([])
  const [filteredActivities, setFilteredActivities] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('すべて')
  const [loading, setLoading] = useState(true)
  const [categories, setCategories] = useState(['すべて'])

  // データを取得する関数
  const fetchActivities = async () => {
    setLoading(true)
    try {
      const activitiesData = await getActivities()
      
      // データを変換
      const formattedActivities = activitiesData.map(activity => ({
        id: activity.ID,
        title: activity.タイトル,
        date: activity.日付,
        category: activity.カテゴリー,
        content: activity.内容,
        image: getImageForActivity(activity.カテゴリー)
      }))

      // 日付順にソート（新しい順）
      const sortedActivities = sortByDate(formattedActivities, 'date', false)
      
      setActivities(sortedActivities)
      setFilteredActivities(sortedActivities)

      // カテゴリー一覧を作成
      const uniqueCategories = ['すべて', ...new Set(sortedActivities.map(activity => activity.category))]
      setCategories(uniqueCategories)
    } catch (error) {
      console.error('活動報告の取得に失敗しました:', error)
    } finally {
      setLoading(false)
    }
  }

  // カテゴリーに応じた画像を取得する関数
  const getImageForActivity = (category) => {
    switch (category) {
      case '行事':
      case '文化祭':
        return festival
      case 'ボランティア':
      case '地域交流':
        return schoolEvent
      default:
        return schoolBuilding
    }
  }

  // カテゴリーフィルターを適用
  const handleCategoryChange = (category) => {
    setSelectedCategory(category)
    const filtered = filterByCategory(activities, category, 'category')
    setFilteredActivities(filtered)
  }

  useEffect(() => {
    fetchActivities()
  }, [])

  return (
    <div className="min-h-screen pt-20 bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <motion.div 
          className="flex justify-between items-center mb-8"
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
        >
          <h1 className="text-4xl font-bold text-gray-900">活動報告</h1>
          <Button 
            onClick={fetchActivities} 
            variant="outline" 
            size="sm"
            disabled={loading}
            className="flex items-center"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            更新
          </Button>
        </motion.div>

        {/* フィルター */}
        <motion.div 
          className="mb-8"
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.8 }}
        >
          <div className="flex items-center space-x-4">
            <Filter className="h-5 w-5 text-gray-600" />
            <Select value={selectedCategory} onValueChange={handleCategoryChange}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="カテゴリーを選択" />
              </SelectTrigger>
              <SelectContent>
                {categories.map(category => (
                  <SelectItem key={category} value={category}>
                    {category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </motion.div>

        {/* ローディング状態 */}
        {loading && (
          <div className="flex justify-center items-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
            <span className="ml-3 text-gray-600">読み込み中...</span>
          </div>
        )}

        {/* 活動報告一覧 */}
        {!loading && (
          <div className="space-y-8">
            {filteredActivities.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-500">該当する活動報告がありません。</p>
              </div>
            ) : (
              filteredActivities.map((activity, index) => (
                <motion.div
                  key={activity.id}
                  initial={{ y: 50, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: index * 0.1, duration: 0.8 }}
                >
                  <Card className="overflow-hidden hover:shadow-lg transition-shadow duration-300">
                    <div className="md:flex">
                      <div className="md:w-1/3">
                        <img 
                          src={activity.image} 
                          alt={activity.title}
                          className="w-full h-48 md:h-full object-cover"
                        />
                      </div>
                      <div className="md:w-2/3 p-6">
                        <div className="flex justify-between items-start mb-4">
                          <Badge variant="secondary">{activity.category}</Badge>
                          <span className="text-sm text-gray-500">{activity.date}</span>
                        </div>
                        <h2 className="text-2xl font-bold text-gray-900 mb-4">{activity.title}</h2>
                        <p className="text-gray-600 leading-relaxed">{activity.content}</p>
                      </div>
                    </div>
                  </Card>
                </motion.div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// お知らせページ
function AnnouncementsPage() {
  const [announcements, setAnnouncements] = useState([])
  const [filteredAnnouncements, setFilteredAnnouncements] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('すべて')
  const [loading, setLoading] = useState(true)
  const [categories, setCategories] = useState(['すべて'])

  // データを取得する関数
  const fetchAnnouncements = async () => {
    setLoading(true)
    try {
      const announcementsData = await getAnnouncements()
      
      // データを変換
      const formattedAnnouncements = announcementsData.map(announcement => ({
        id: announcement.ID,
        title: announcement.タイトル,
        date: announcement.日付,
        category: announcement.カテゴリー,
        important: announcement.重要,
        content: announcement.内容
      }))

      // 重要度と日付順にソート
      const sortedAnnouncements = sortAnnouncementsByImportance(formattedAnnouncements)
      
      setAnnouncements(sortedAnnouncements)
      setFilteredAnnouncements(sortedAnnouncements)

      // カテゴリー一覧を作成
      const uniqueCategories = ['すべて', ...new Set(sortedAnnouncements.map(announcement => announcement.category))]
      setCategories(uniqueCategories)
    } catch (error) {
      console.error('お知らせの取得に失敗しました:', error)
    } finally {
      setLoading(false)
    }
  }

  // カテゴリーフィルターを適用
  const handleCategoryChange = (category) => {
    setSelectedCategory(category)
    const filtered = filterByCategory(announcements, category, 'category')
    const sortedFiltered = sortAnnouncementsByImportance(filtered)
    setFilteredAnnouncements(sortedFiltered)
  }

  useEffect(() => {
    fetchAnnouncements()
  }, [])

  return (
    <div className="min-h-screen pt-20 bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <motion.div 
          className="flex justify-between items-center mb-8"
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
        >
          <h1 className="text-4xl font-bold text-gray-900">お知らせ</h1>
          <Button 
            onClick={fetchAnnouncements} 
            variant="outline" 
            size="sm"
            disabled={loading}
            className="flex items-center"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            更新
          </Button>
        </motion.div>

        {/* フィルター */}
        <motion.div 
          className="mb-8"
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.8 }}
        >
          <div className="flex items-center space-x-4">
            <Filter className="h-5 w-5 text-gray-600" />
            <Select value={selectedCategory} onValueChange={handleCategoryChange}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="カテゴリーを選択" />
              </SelectTrigger>
              <SelectContent>
                {categories.map(category => (
                  <SelectItem key={category} value={category}>
                    {category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </motion.div>

        {/* ローディング状態 */}
        {loading && (
          <div className="flex justify-center items-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
            <span className="ml-3 text-gray-600">読み込み中...</span>
          </div>
        )}

        {/* お知らせ一覧 */}
        {!loading && (
          <div className="space-y-6">
            {filteredAnnouncements.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-500">該当するお知らせがありません。</p>
              </div>
            ) : (
              filteredAnnouncements.map((announcement, index) => (
                <motion.div
                  key={announcement.id}
                  initial={{ y: 50, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: index * 0.1, duration: 0.8 }}
                >
                  <Card className={`hover:shadow-lg transition-shadow duration-300 ${
                    announcement.important ? 'border-l-4 border-l-red-500 bg-red-50' : ''
                  }`}>
                    <CardHeader>
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center space-x-2">
                          <Badge 
                            variant={announcement.important ? "destructive" : "secondary"}
                          >
                            {announcement.category}
                          </Badge>
                          {announcement.important && (
                            <Star className="h-4 w-4 text-red-500 fill-current" />
                          )}
                        </div>
                        <span className="text-sm text-gray-500">{announcement.date}</span>
                      </div>
                      <CardTitle className="text-xl">{announcement.title}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-gray-600 leading-relaxed">{announcement.content}</p>
                    </CardContent>
                  </Card>
                </motion.div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// 提出物ページ
function SubmissionsPage() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [name, setName] = useState('')
  const [gradeClass, setGradeClass] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [dragActive, setDragActive] = useState(false)

  // ファイル選択処理
  const handleFileSelect = (file) => {
    // ファイル形式チェック
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/gif']
    if (!allowedTypes.includes(file.type)) {
      alert('PDF、JPEG、PNG、GIFファイルのみ提出可能です。')
      return
    }

    // ファイルサイズチェック（10MB制限）
    if (file.size > 10 * 1024 * 1024) {
      alert('ファイルサイズは10MB以下にしてください。')
      return
    }

    setSelectedFile(file)
    setUploadResult(null)
  }

  // ドラッグ&ドロップ処理
  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  // ファイル入力処理
  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0])
    }
  }

  // 提出処理
  const handleSubmit = async () => {
    if (!selectedFile || !name.trim() || !gradeClass.trim()) {
      alert('すべての項目を入力してください。')
      return
    }

    setUploading(true)
    try {
      const result = await submitFile(selectedFile, name.trim(), gradeClass.trim())
      setUploadResult({ success: true, message: '提出が完了しました。' })
      
      // フォームをリセット
      setSelectedFile(null)
      setName('')
      setGradeClass('')
    } catch (error) {
      setUploadResult({ success: false, message: '提出に失敗しました。もう一度お試しください。' })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen pt-20 bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <motion.h1 
          className="text-4xl font-bold text-gray-900 mb-8"
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
        >
          提出物
        </motion.h1>

        <motion.div
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.8 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>提出物アップロード</CardTitle>
              <CardDescription>
                PDF、画像ファイル（JPEG、PNG、GIF）のみ提出可能です。ファイルサイズは10MB以下にしてください。
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* ファイルアップロードエリア */}
                <div 
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    dragActive 
                      ? 'border-blue-500 bg-blue-50' 
                      : selectedFile 
                        ? 'border-green-500 bg-green-50' 
                        : 'border-gray-300'
                  }`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                >
                  <Upload className={`h-12 w-12 mx-auto mb-4 ${
                    selectedFile ? 'text-green-500' : 'text-gray-400'
                  }`} />
                  
                  {selectedFile ? (
                    <div>
                      <p className="text-green-600 font-medium mb-2">選択されたファイル:</p>
                      <p className="text-gray-700 mb-4">{selectedFile.name}</p>
                      <p className="text-sm text-gray-500 mb-4">
                        サイズ: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-gray-600 mb-4">
                        ファイルをドラッグ&ドロップまたはクリックして選択
                      </p>
                    </div>
                  )}
                  
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png,.gif"
                    onChange={handleFileInput}
                    className="hidden"
                    id="file-input"
                  />
                  <label htmlFor="file-input">
                    <Button variant={selectedFile ? "outline" : "default"} asChild>
                      <span className="cursor-pointer">
                        {selectedFile ? 'ファイルを変更' : 'ファイルを選択'}
                      </span>
                    </Button>
                  </label>
                </div>
                
                {/* 提出者情報 */}
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      お名前 <span className="text-red-500">*</span>
                    </label>
                    <input 
                      type="text" 
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="山田 太郎"
                      disabled={uploading}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      学年・クラス <span className="text-red-500">*</span>
                    </label>
                    <input 
                      type="text" 
                      value={gradeClass}
                      onChange={(e) => setGradeClass(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="2年A組"
                      disabled={uploading}
                    />
                  </div>
                </div>

                {/* 結果表示 */}
                {uploadResult && (
                  <div className={`p-4 rounded-md ${
                    uploadResult.success 
                      ? 'bg-green-50 border border-green-200 text-green-700' 
                      : 'bg-red-50 border border-red-200 text-red-700'
                  }`}>
                    {uploadResult.message}
                  </div>
                )}
                
                {/* 提出ボタン */}
                <Button 
                  className="w-full" 
                  onClick={handleSubmit}
                  disabled={!selectedFile || !name.trim() || !gradeClass.trim() || uploading}
                >
                  {uploading ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      提出中...
                    </>
                  ) : (
                    '提出する'
                  )}
                </Button>

                {/* 注意事項 */}
                <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                  <h3 className="font-medium text-blue-900 mb-2">提出に関する注意事項</h3>
                  <ul className="text-sm text-blue-700 space-y-1">
                    <li>• 提出可能なファイル形式: PDF、JPEG、PNG、GIF</li>
                    <li>• ファイルサイズ上限: 10MB</li>
                    <li>• 提出回数に制限はありません</li>
                    <li>• 提出されたファイルは生徒会役員と教員のみが閲覧できます</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}

// フッターコンポーネント
function Footer() {
  return (
    <footer className="bg-gray-900 text-white py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid md:grid-cols-3 gap-8">
          <div>
            <h3 className="text-lg font-semibold mb-4">千葉英和高等学校 生徒会</h3>
            <p className="text-gray-400 text-sm">
              〒275-8511<br />
              千葉県習志野市実籾本郷22-1<br />
              TEL: 047-474-5001
            </p>
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-4">リンク</h3>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><a href="#" className="hover:text-white transition-colors">学校公式サイト</a></li>
              <li><a href="#" className="hover:text-white transition-colors">プライバシーポリシー</a></li>
              <li><a href="#" className="hover:text-white transition-colors">サイトマップ</a></li>
            </ul>
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-4">SNS</h3>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><a href="#" className="hover:text-white transition-colors">Instagram</a></li>
              <li><a href="#" className="hover:text-white transition-colors">X (Twitter)</a></li>
              <li><a href="#" className="hover:text-white transition-colors">YouTube</a></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-gray-800 mt-8 pt-8 text-center text-sm text-gray-400">
          <p>&copy; 2025 千葉英和高等学校生徒会. All rights reserved.</p>
        </div>
      </div>
    </footer>
  )
}

// メインアプリコンポーネント
function App() {
  return (
    <Router>
      <div className="App">
        <Navigation />
        <main>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/activities" element={<ActivitiesPage />} />
            <Route path="/announcements" element={<AnnouncementsPage />} />
            <Route path="/submissions" element={<SubmissionsPage />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </Router>
  )
}

export default App
