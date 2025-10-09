// Google Apps Script API サービス

const GAS_WEB_APP_URL = 'https://script.google.com/macros/s/AKfycbxUd4o7nh8byOan6ruke9JAWc8d8oZ0rkxNLroARnNwG3JVseh5OjR2LQ9ctVRGmO3epA/exec';

/**
 * 活動報告データを取得する
 */
export const getActivities = async () => {
  try {
    const response = await fetch(`${GAS_WEB_APP_URL}?path=activities`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const text = await response.text();
    const data = JSON.parse(text);
    return data;
  } catch (error) {
    console.error('活動報告の取得に失敗しました:', error);
    // フォールバック用のサンプルデータを返す
    return [
      {
        ID: 1,
        タイトル: '文化祭実行委員会の募集について',
        日付: '2025-10-05',
        カテゴリー: '行事',
        内容: '今年度の文化祭実行委員を募集しています。多くの皆さんの参加をお待ちしています。',
        画像URL: '/src/assets/festival.jpg'
      },
      {
        ID: 2,
        タイトル: '生徒会役員選挙の実施について',
        日付: '2025-10-03',
        カテゴリー: '選挙',
        内容: '来年度の生徒会役員選挙を実施します。立候補の受付を開始しました。',
        画像URL: '/src/assets/school-event.jpg'
      },
      {
        ID: 3,
        タイトル: '地域清掃ボランティア活動報告',
        日付: '2025-10-01',
        カテゴリー: 'ボランティア',
        内容: '先日実施した地域清掃活動に多くの生徒が参加しました。',
        画像URL: '/src/assets/school-building.jpg'
      }
    ];
  }
};

/**
 * お知らせデータを取得する
 */
export const getAnnouncements = async () => {
  try {
    const response = await fetch(`${GAS_WEB_APP_URL}?path=announcements`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const text = await response.text();
    const data = JSON.parse(text);
    return data;
  } catch (error) {
    console.error('お知らせの取得に失敗しました:', error);
    // フォールバック用のサンプルデータを返す
    return [
      {
        ID: 1,
        タイトル: '体育祭の日程変更について',
        日付: '2025-10-06',
        カテゴリー: '緊急',
        重要: true,
        内容: '天候の影響により、体育祭の日程を変更いたします。詳細は後日お知らせします。'
      },
      {
        ID: 2,
        タイトル: '図書委員会からのお知らせ',
        日付: '2025-10-04',
        カテゴリー: '委員会',
        重要: false,
        内容: '新刊図書の紹介と図書館利用についてのお知らせです。'
      },
      {
        ID: 3,
        タイトル: '制服着用についての注意事項',
        日付: '2025-10-02',
        カテゴリー: '生活指導',
        重要: false,
        内容: '制服の正しい着用方法について改めてお知らせします。'
      }
    ];
  }
};

/**
 * 提出物をアップロードする
 */
export const submitFile = async (fileData, name, gradeClass) => {
  try {
    const formData = new FormData();
    formData.append('path', 'submit');
    formData.append('name', name);
    formData.append('gradeClass', gradeClass);
    
    // ファイルをBase64エンコードして送信
    const reader = new FileReader();
    return new Promise((resolve, reject) => {
      reader.onload = async () => {
        const base64Data = reader.result.split(',')[1];
        formData.append('file', base64Data);
        formData.append('filename', fileData.name);
        formData.append('mimeType', fileData.type);

        try {
          const response = await fetch(GAS_WEB_APP_URL, {
            method: 'POST',
            body: formData
          });
          
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          
          const result = await response.json();
          resolve(result);
        } catch (error) {
          reject(error);
        }
      };
      reader.onerror = () => reject(new Error('ファイルの読み込みに失敗しました'));
      reader.readAsDataURL(fileData);
    });
  } catch (error) {
    console.error('ファイルの提出に失敗しました:', error);
    throw error;
  }
};

/**
 * データを日付順にソートする
 */
export const sortByDate = (data, dateField = '日付', ascending = false) => {
  return [...data].sort((a, b) => {
    const dateA = new Date(a[dateField]);
    const dateB = new Date(b[dateField]);
    return ascending ? dateA - dateB : dateB - dateA;
  });
};

/**
 * カテゴリーでフィルタリングする
 */
export const filterByCategory = (data, category, categoryField = 'カテゴリー') => {
  if (!category || category === 'すべて') {
    return data;
  }
  return data.filter(item => item[categoryField] === category);
};

/**
 * 重要なお知らせを上部に固定する
 */
export const sortAnnouncementsByImportance = (announcements) => {
  return [...announcements].sort((a, b) => {
    // 重要なお知らせを上部に表示
    if (a.重要 && !b.重要) return -1;
    if (!a.重要 && b.重要) return 1;
    
    // 同じ重要度の場合は日付順（新しい順）
    const dateA = new Date(a.日付);
    const dateB = new Date(b.日付);
    return dateB - dateA;
  });
};
