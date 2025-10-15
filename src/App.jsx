import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Calendar, Users, FileText, Upload, ChevronRight, ArrowLeft, Clock, Tag } from 'lucide-react'
import { getActivities, getAnnouncements } from './services/api'
import './App.css'

// 画像のインポート
import studentCouncilMeeting from './assets/student-council-meeting.jpg'
import studentActivities from './assets/student-activities.jpg'
import studentGroup from './assets/student-group.jpg'

function App() {
  const [currentPage, setCurrentPage] = useState('home')
  const [selectedActivity, setSelectedActivity] = useState(null)
  const [selectedAnnouncement, setSelectedAnnouncement] = useState(null)

  const colorPalette = {
    primary: 'from-blue-600 to-blue-700',
    secondary: 'from-emerald-500 to-emerald-600',
    accent: 'from-purple-500 to-purple-600',
    warm: 'from-orange-500 to-orange-600'
  }

  const getImageForActivity = (category) => {
    switch (category) {
      case '行事':
        return studentActivities
      case '会議':
        return studentCouncilMeeting
      case 'ボランティア':
        return studentGroup
      default:
        return studentActivities
    }
  }

  const renderPage = () => {
    switch (currentPage) {
      case 'activities':
        return <ActivitiesPage onActivityClick={setSelectedActivity} />
      case 'announcements':
        return <AnnouncementsPage onAnnouncementClick={setSelectedAnnouncement} />
      case 'submissions':
        return <SubmissionsPage />
      default:
        return <HomePage onActivityClick={setSelectedActivity} onAnnouncementClick={setSelectedAnnouncement} />
    }
  }

  if (selectedActivity) {
    return <ActivityDetailPage activity={selectedActivity} onBack={() => setSelectedActivity(null)} />
  }

  if (selectedAnnouncement) {
    return <AnnouncementDetailPage announcement={selectedAnnouncement} onBack={() => setSelectedAnnouncement(null)} />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ヘッダー */}
      <header className="bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <Users className="h-8 w-8" />
              <h1 className="text-xl font-bold">千葉英和高校生徒会</h1>
            </div>
            <nav className="hidden md:flex space-x-8">
              {[
                { key: 'home', label: 'ホーム', icon: Users },
                { key: 'activities', label: '活動報告', icon: Calendar },
                { key: 'announcements', label: 'お知らせ', icon: FileText },
                { key: 'submissions', label: '提出物', icon: Upload }
              ].map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => setCurrentPage(key)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md transition-colors ${
                    currentPage === key
                      ? 'bg-blue-800 text-white'
                      : 'text-blue-100 hover:bg-blue-700 hover:text-white'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>
      </header>

      {/* メインコンテンツ */}
      <main>
        <AnimatePresence mode="wait">
          {renderPage()}
        </AnimatePresence>
      </main>

      {/* フッター */}
      <footer className="bg-gray-800 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-8">
            <div>
              <h3 className="text-lg font-semibold mb-4">千葉英和高校 生徒会</h3>
              <p className="text-gray-300">
                生徒の皆さんの声を大切にし、より良い学校生活の実現を目指しています。
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-4">リンク</h3>
              <ul className="space-y-2 text-gray-300">
                <li><a href="#" className="hover:text-white transition-colors">学校公式サイト</a></li>
                <li><a href="#" className="hover:text-white transition-colors">在校生向け情報</a></li>
                <li><a href="#" className="hover:text-white transition-colors">保護者向け情報</a></li>
              </ul>
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-4">SNS</h3>
              <div className="flex space-x-4">
                <a href="#" className="text-gray-300 hover:text-white transition-colors">Twitter</a>
                <a href="#" className="text-gray-300 hover:text-white transition-colors">Instagram</a>
                <a href="#" className="text-gray-300 hover:text-white transition-colors">Facebook</a>
              </div>
            </div>
          </div>
          <div className="border-t border-gray-700 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2024 千葉英和高校生徒会. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

// ホームページ
function HomePage({ onActivityClick, onAnnouncementClick }) {
  const [activities, setActivities] = useState([])
  const [announcements, setAnnouncements] = useState([])
  const [loading, setLoading] = useState(true)

  const colorPalette = {
    primary: 'from-blue-600 to-blue-700',
    secondary: 'from-emerald-500 to-emerald-600',
    accent: 'from-purple-500 to-purple-600',
    warm: 'from-orange-500 to-orange-600'
  }

  const getImageForActivity = (category) => {
    switch (category) {
      case '行事':
        return studentActivities
      case '会議':
        return studentCouncilMeeting
      case 'ボランティア':
        return studentGroup
      default:
        return studentActivities
    }
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [activitiesData, announcementsData] = await Promise.all([
          getActivities(),
          getAnnouncements()
        ])
        setActivities(activitiesData.slice(0, 3))
        setAnnouncements(announcementsData.slice(0, 3))
      } catch (error) {
        console.error('データの取得に失敗しました:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  return (
    <div className="space-y-0">
      {/* ヒーローセクション */}
      <section className="relative h-screen flex items-center justify-center overflow-hidden">
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{ 
            backgroundImage: `url(${studentGroup})`,
            filter: 'brightness(0.4)'
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-blue-900/50 to-purple-900/50" />
        <motion.div 
          className="relative z-10 text-center text-white px-4"
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1 }}
        >
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
            千葉英和高校生徒会
          </h1>
          <p className="text-xl md:text-2xl mb-8 text-blue-100">
            Student Council of Chiba Eiwa High School
          </p>
          <motion.button
            className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-8 py-4 rounded-full text-lg font-semibold shadow-lg transition-all duration-300 transform hover:scale-105"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            活動を見る
            <ChevronRight className="inline ml-2 h-5 w-5" />
          </motion.button>
        </motion.div>
      </section>

      {/* 生徒会紹介セクション */}
      <section className="py-20 bg-white">
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
              千葉英和高校生徒会は、生徒の皆さんの声を大切にし、より良い学校生活の実現を目指しています。
              文化祭や体育祭などの学校行事の企画・運営、地域との交流活動、生徒の意見を学校に届ける橋渡し役として、
              日々活動しています。皆さんの学校生活がより充実したものになるよう、一緒に頑張りましょう。
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Calendar,
                title: '企画・運営',
                description: '学校行事の企画・運営',
                color: 'from-blue-500 to-blue-600'
              },
              {
                icon: Users,
                title: '意見集約',
                description: '生徒の声を届ける',
                color: 'from-emerald-500 to-emerald-600'
              },
              {
                icon: FileText,
                title: '地域交流',
                description: '地域との連携活動',
                color: 'from-purple-500 to-purple-600'
              }
            ].map((item, index) => (
              <motion.div
                key={index}
                initial={{ y: 50, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                transition={{ delay: index * 0.2, duration: 0.8 }}
                viewport={{ once: true }}
                className="text-center p-8 bg-white rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300"
              >
                <div className={`inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r ${item.color} text-white rounded-full mb-6`}>
                  <item.icon className="h-8 w-8" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4">{item.title}</h3>
                <p className="text-gray-600">{item.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* 最新の活動報告 */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center mb-12">
            <motion.h2 
              className="text-3xl font-bold text-gray-900"
              initial={{ x: -50, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
            >
              最新の活動報告
            </motion.h2>
            <motion.a
              href="#"
              className="text-blue-600 hover:text-blue-800 font-medium flex items-center"
              initial={{ x: 50, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
            >
              すべて見る
              <ChevronRight className="ml-1 h-4 w-4" />
            </motion.a>
          </div>

          {loading ? (
            <div className="grid md:grid-cols-3 gap-8">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-lg shadow-md overflow-hidden animate-pulse">
                  <div className="h-48 bg-gray-300"></div>
                  <div className="p-6">
                    <div className="h-4 bg-gray-300 rounded mb-2"></div>
                    <div className="h-4 bg-gray-300 rounded mb-4 w-3/4"></div>
                    <div className="h-3 bg-gray-300 rounded"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <motion.div 
              className="grid md:grid-cols-3 gap-8"
              initial={{ y: 50, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
            >
              {activities.map((activity, index) => (
                <motion.div
                  key={activity.id}
                  initial={{ y: 50, opacity: 0 }}
                  whileInView={{ y: 0, opacity: 1 }}
                  transition={{ delay: index * 0.1, duration: 0.8 }}
                  viewport={{ once: true }}
                  whileHover={{ y: -5 }}
                  className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-all duration-300 cursor-pointer"
                  onClick={() => onActivityClick(activity)}
                >
                  <div className="aspect-video overflow-hidden">
                    <img 
                      src={getImageForActivity(activity.category)} 
                      alt={activity.title}
                      className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                    />
                  </div>
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-2">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium bg-gradient-to-r ${colorPalette.primary} text-white`}>
                        {activity.category}
                      </span>
                      <span className="text-sm text-gray-500">{activity.date}</span>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">{activity.title}</h3>
                    <p className="text-gray-600 text-sm line-clamp-3">{activity.excerpt}</p>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>
      </section>

      {/* お知らせ */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center mb-12">
            <motion.h2 
              className="text-3xl font-bold text-gray-900"
              initial={{ x: -50, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
            >
              お知らせ
            </motion.h2>
            <motion.button
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
              initial={{ x: 50, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
            >
              すべて見る
            </motion.button>
          </div>

          <motion.div 
            className="space-y-4"
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            {announcements.map((announcement, index) => (
              <motion.div
                key={announcement.id}
                initial={{ x: -50, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1 }}
                transition={{ delay: index * 0.1, duration: 0.8 }}
                viewport={{ once: true }}
                className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => onAnnouncementClick(announcement)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      {announcement.important && (
                        <span className="bg-red-100 text-red-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
                          重要
                        </span>
                      )}
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium bg-gradient-to-r ${colorPalette.secondary} text-white`}>
                        {announcement.category}
                      </span>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">{announcement.title}</h3>
                    <p className="text-gray-600 text-sm line-clamp-2">{announcement.excerpt}</p>
                  </div>
                  <span className="text-sm text-gray-500 ml-4">{announcement.date}</span>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* 生徒会組織図 */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            className="text-center mb-16"
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl font-bold text-gray-900 mb-6">生徒会組織図</h2>
            <p className="text-lg text-gray-600">
              千葉英和高校の生徒会組織構造をご紹介します
            </p>
          </motion.div>

          {/* 組織図 */}
          <div className="bg-gradient-to-br from-gray-50 to-white rounded-xl shadow-lg p-8 overflow-x-auto">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
              className="flex justify-center"
            >
              <img 
                src="/seitokai_org_chart.svg" 
                alt="千葉英和高校生徒会組織図" 
                className="max-w-full h-auto"
                style={{ maxHeight: '800px' }}
              />
            </motion.div>
          </div>
        </div>
      </section>
    </div>
  )
}

// 活動報告ページ
function ActivitiesPage({ onActivityClick }) {
  const [activities, setActivities] = useState([])
  const [filteredActivities, setFilteredActivities] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('すべて')
  const [loading, setLoading] = useState(true)
  const [categories, setCategories] = useState(['すべて'])

  const colorPalette = {
    primary: 'from-blue-600 to-blue-700',
    secondary: 'from-emerald-500 to-emerald-600',
    accent: 'from-purple-500 to-purple-600',
    warm: 'from-orange-500 to-orange-600'
  }

  const getImageForActivity = (category) => {
    switch (category) {
      case '行事':
        return studentActivities
      case '会議':
        return studentCouncilMeeting
      case 'ボランティア':
        return studentGroup
      default:
        return studentActivities
    }
  }

  useEffect(() => {
    const fetchActivities = async () => {
      try {
        const data = await getActivities()
        setActivities(data)
        setFilteredActivities(data)
        
        const uniqueCategories = ['すべて', ...new Set(data.map(activity => activity.category))]
        setCategories(uniqueCategories)
      } catch (error) {
        console.error('活動報告の取得に失敗しました:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchActivities()
  }, [])

  useEffect(() => {
    if (selectedCategory === 'すべて') {
      setFilteredActivities(activities)
    } else {
      setFilteredActivities(activities.filter(activity => activity.category === selectedCategory))
    }
  }, [selectedCategory, activities])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-gray-50 py-12"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl font-bold text-gray-900 mb-4">活動報告</h1>
          <p className="text-lg text-gray-600">生徒会の最新活動をご報告します</p>
        </motion.div>

        {/* カテゴリーフィルター */}
        <motion.div
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="flex flex-wrap justify-center gap-4 mb-12"
        >
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={`px-6 py-3 rounded-full font-medium transition-all duration-300 ${
                selectedCategory === category
                  ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg'
                  : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
              }`}
            >
              {category}
            </button>
          ))}
        </motion.div>

        {/* 活動一覧 */}
        {loading ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="bg-white rounded-lg shadow-md overflow-hidden animate-pulse">
                <div className="h-48 bg-gray-300"></div>
                <div className="p-6">
                  <div className="h-4 bg-gray-300 rounded mb-2"></div>
                  <div className="h-4 bg-gray-300 rounded mb-4 w-3/4"></div>
                  <div className="h-3 bg-gray-300 rounded"></div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="grid md:grid-cols-2 lg:grid-cols-3 gap-8"
          >
            {filteredActivities.map((activity, index) => (
              <motion.div
                key={activity.id}
                initial={{ y: 50, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: index * 0.1, duration: 0.8 }}
                whileHover={{ y: -5 }}
                className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-all duration-300 cursor-pointer"
                onClick={() => onActivityClick(activity)}
              >
                <div className="aspect-video overflow-hidden">
                  <img 
                    src={getImageForActivity(activity.category)} 
                    alt={activity.title}
                    className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                  />
                </div>
                <div className="p-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium bg-gradient-to-r ${colorPalette.primary} text-white`}>
                      {activity.category}
                    </span>
                    <span className="text-sm text-gray-500">{activity.date}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">{activity.title}</h3>
                  <p className="text-gray-600 text-sm line-clamp-3">{activity.excerpt}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}

// お知らせページ
function AnnouncementsPage({ onAnnouncementClick }) {
  const [announcements, setAnnouncements] = useState([])
  const [filteredAnnouncements, setFilteredAnnouncements] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('すべて')
  const [loading, setLoading] = useState(true)
  const [categories, setCategories] = useState(['すべて'])

  const colorPalette = {
    primary: 'from-blue-600 to-blue-700',
    secondary: 'from-emerald-500 to-emerald-600',
    accent: 'from-purple-500 to-purple-600',
    warm: 'from-orange-500 to-orange-600'
  }

  useEffect(() => {
    const fetchAnnouncements = async () => {
      try {
        const data = await getAnnouncements()
        setAnnouncements(data)
        setFilteredAnnouncements(data)
        
        const uniqueCategories = ['すべて', ...new Set(data.map(announcement => announcement.category))]
        setCategories(uniqueCategories)
      } catch (error) {
        console.error('お知らせの取得に失敗しました:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchAnnouncements()
  }, [])

  useEffect(() => {
    if (selectedCategory === 'すべて') {
      setFilteredAnnouncements(announcements)
    } else {
      setFilteredAnnouncements(announcements.filter(announcement => announcement.category === selectedCategory))
    }
  }, [selectedCategory, announcements])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-gray-50 py-12"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl font-bold text-gray-900 mb-4">お知らせ</h1>
          <p className="text-lg text-gray-600">生徒会からの重要なお知らせをお届けします</p>
        </motion.div>

        {/* カテゴリーフィルター */}
        <motion.div
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="flex flex-wrap justify-center gap-4 mb-12"
        >
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={`px-6 py-3 rounded-full font-medium transition-all duration-300 ${
                selectedCategory === category
                  ? 'bg-gradient-to-r from-emerald-500 to-emerald-600 text-white shadow-lg'
                  : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
              }`}
            >
              {category}
            </button>
          ))}
        </motion.div>

        {/* お知らせ一覧 */}
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="bg-white border border-gray-200 rounded-lg p-6 animate-pulse">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <div className="h-6 bg-gray-300 rounded-full w-16"></div>
                      <div className="h-6 bg-gray-300 rounded-full w-20"></div>
                    </div>
                    <div className="h-6 bg-gray-300 rounded mb-2 w-3/4"></div>
                    <div className="h-4 bg-gray-300 rounded w-full"></div>
                  </div>
                  <div className="h-4 bg-gray-300 rounded w-20 ml-4"></div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="space-y-4"
          >
            {filteredAnnouncements.map((announcement, index) => (
              <motion.div
                key={announcement.id}
                initial={{ x: -50, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: index * 0.1, duration: 0.8 }}
                className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => onAnnouncementClick(announcement)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      {announcement.important && (
                        <span className="bg-red-100 text-red-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
                          重要
                        </span>
                      )}
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium bg-gradient-to-r ${colorPalette.secondary} text-white`}>
                        {announcement.category}
                      </span>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">{announcement.title}</h3>
                    <p className="text-gray-600 text-sm line-clamp-2">{announcement.excerpt}</p>
                  </div>
                  <span className="text-sm text-gray-500 ml-4">{announcement.date}</span>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}

// 提出物ページ
function SubmissionsPage() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-gray-50 py-12"
    >
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl font-bold text-gray-900 mb-4">提出物</h1>
          <p className="text-lg text-gray-600">生徒会への提出物はこちらから</p>
        </motion.div>

        <motion.div
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="bg-white rounded-lg shadow-lg p-8"
        >
          <div className="text-center mb-8">
            <Upload className="h-16 w-16 text-blue-600 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">ファイルをアップロード</h2>
            <p className="text-gray-600">PDF、画像ファイル（JPG、PNG）に対応しています</p>
          </div>

          <form className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                お名前 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="山田 太郎"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  学年 <span className="text-red-500">*</span>
                </label>
                <select className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                  <option value="">選択してください</option>
                  <option value="1">1年</option>
                  <option value="2">2年</option>
                  <option value="3">3年</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  クラス <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="A"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                提出物の種類 <span className="text-red-500">*</span>
              </label>
              <select className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                <option value="">選択してください</option>
                <option value="application">各種申請書</option>
                <option value="report">活動報告書</option>
                <option value="proposal">企画提案書</option>
                <option value="other">その他</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                ファイル <span className="text-red-500">*</span>
              </label>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors">
                <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600 mb-2">ファイルをドラッグ&ドロップ、または</p>
                <button
                  type="button"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                >
                  ファイルを選択
                </button>
                <p className="text-sm text-gray-500 mt-2">最大ファイルサイズ: 10MB</p>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                備考
              </label>
              <textarea
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="追加の説明があれば記入してください"
              ></textarea>
            </div>

            <div className="text-center">
              <button
                type="submit"
                className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white px-8 py-3 rounded-lg font-medium transition-all duration-300 transform hover:scale-105"
              >
                提出する
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </motion.div>
  )
}

// 活動詳細ページ
function ActivityDetailPage({ activity, onBack }) {
  const getImageForActivity = (category) => {
    switch (category) {
      case '行事':
        return studentActivities
      case '会議':
        return studentCouncilMeeting
      case 'ボランティア':
        return studentGroup
      default:
        return studentActivities
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-gray-50"
    >
      {/* ヘッダー */}
      <header className="bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center py-4">
            <button
              onClick={onBack}
              className="flex items-center space-x-2 text-blue-100 hover:text-white transition-colors mr-6"
            >
              <ArrowLeft className="h-5 w-5" />
              <span>戻る</span>
            </button>
            <div className="flex items-center space-x-3">
              <Users className="h-8 w-8" />
              <h1 className="text-xl font-bold">千葉英和高校生徒会</h1>
            </div>
          </div>
        </div>
      </header>

      {/* メインコンテンツ */}
      <main className="py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.article
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            className="bg-white rounded-lg shadow-lg overflow-hidden"
          >
            {/* ヘッダー画像 */}
            <div className="aspect-video overflow-hidden">
              <img 
                src={getImageForActivity(activity.category)} 
                alt={activity.title}
                className="w-full h-full object-cover"
              />
            </div>

            {/* 記事内容 */}
            <div className="p-8">
              {/* メタ情報 */}
              <div className="flex items-center space-x-4 mb-6">
                <span className="inline-block px-3 py-1 rounded-full text-sm font-medium bg-gradient-to-r from-blue-600 to-blue-700 text-white">
                  {activity.category}
                </span>
                <div className="flex items-center text-gray-500 text-sm">
                  <Clock className="h-4 w-4 mr-1" />
                  {activity.date}
                </div>
              </div>

              {/* タイトル */}
              <h1 className="text-3xl font-bold text-gray-900 mb-6">{activity.title}</h1>

              {/* 本文 */}
              <div className="prose prose-lg max-w-none">
                <p className="text-gray-700 leading-relaxed mb-6">
                  {activity.content || activity.excerpt}
                </p>
                
                {/* 追加の詳細内容 */}
                <div className="space-y-4">
                  <h3 className="text-xl font-semibold text-gray-900">活動の詳細</h3>
                  <p className="text-gray-700 leading-relaxed">
                    この活動では、生徒の皆さんの積極的な参加により、素晴らしい成果を上げることができました。
                    今後もこのような取り組みを通じて、学校生活をより充実したものにしていきたいと考えています。
                  </p>
                  
                  <h3 className="text-xl font-semibold text-gray-900">参加者の声</h3>
                  <blockquote className="border-l-4 border-blue-500 pl-4 italic text-gray-700">
                    「とても有意義な活動でした。多くの学びがあり、今後の学校生活に活かしていきたいと思います。」
                  </blockquote>
                  
                  <h3 className="text-xl font-semibold text-gray-900">今後の予定</h3>
                  <p className="text-gray-700 leading-relaxed">
                    次回の活動は来月を予定しています。詳細が決まり次第、改めてお知らせいたします。
                    多くの皆さんのご参加をお待ちしています。
                  </p>
                </div>
              </div>

              {/* タグ */}
              <div className="mt-8 pt-6 border-t border-gray-200">
                <div className="flex items-center space-x-2">
                  <Tag className="h-4 w-4 text-gray-500" />
                  <span className="text-sm text-gray-500">タグ:</span>
                  <span className="inline-block px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded">
                    {activity.category}
                  </span>
                  <span className="inline-block px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded">
                    生徒会活動
                  </span>
                </div>
              </div>
            </div>
          </motion.article>
        </div>
      </main>
    </motion.div>
  )
}

// お知らせ詳細ページ
function AnnouncementDetailPage({ announcement, onBack }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-gray-50"
    >
      {/* ヘッダー */}
      <header className="bg-gradient-to-r from-emerald-500 to-emerald-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center py-4">
            <button
              onClick={onBack}
              className="flex items-center space-x-2 text-emerald-100 hover:text-white transition-colors mr-6"
            >
              <ArrowLeft className="h-5 w-5" />
              <span>戻る</span>
            </button>
            <div className="flex items-center space-x-3">
              <FileText className="h-8 w-8" />
              <h1 className="text-xl font-bold">千葉英和高校生徒会</h1>
            </div>
          </div>
        </div>
      </header>

      {/* メインコンテンツ */}
      <main className="py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.article
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            className="bg-white rounded-lg shadow-lg overflow-hidden"
          >
            <div className="p-8">
              {/* メタ情報 */}
              <div className="flex items-center space-x-4 mb-6">
                {announcement.important && (
                  <span className="bg-red-100 text-red-800 text-sm font-medium px-3 py-1 rounded-full">
                    重要
                  </span>
                )}
                <span className="inline-block px-3 py-1 rounded-full text-sm font-medium bg-gradient-to-r from-emerald-500 to-emerald-600 text-white">
                  {announcement.category}
                </span>
                <div className="flex items-center text-gray-500 text-sm">
                  <Clock className="h-4 w-4 mr-1" />
                  {announcement.date}
                </div>
              </div>

              {/* タイトル */}
              <h1 className="text-3xl font-bold text-gray-900 mb-6">{announcement.title}</h1>

              {/* 本文 */}
              <div className="prose prose-lg max-w-none">
                <p className="text-gray-700 leading-relaxed mb-6">
                  {announcement.content || announcement.excerpt}
                </p>
                
                {/* 追加の詳細内容 */}
                <div className="space-y-4">
                  <h3 className="text-xl font-semibold text-gray-900">詳細情報</h3>
                  <p className="text-gray-700 leading-relaxed">
                    このお知らせに関してご不明な点がございましたら、生徒会までお気軽にお問い合わせください。
                    皆さんのご理解とご協力をお願いいたします。
                  </p>
                  
                  <h3 className="text-xl font-semibold text-gray-900">お問い合わせ</h3>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <p className="text-gray-700">
                      <strong>連絡先:</strong> 生徒会室<br />
                      <strong>受付時間:</strong> 平日 12:30-13:00, 15:30-16:30
                    </p>
                  </div>
                </div>
              </div>

              {/* タグ */}
              <div className="mt-8 pt-6 border-t border-gray-200">
                <div className="flex items-center space-x-2">
                  <Tag className="h-4 w-4 text-gray-500" />
                  <span className="text-sm text-gray-500">タグ:</span>
                  <span className="inline-block px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded">
                    {announcement.category}
                  </span>
                  <span className="inline-block px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded">
                    お知らせ
                  </span>
                </div>
              </div>
            </div>
          </motion.article>
        </div>
      </main>
    </motion.div>
  )
}

export default App
