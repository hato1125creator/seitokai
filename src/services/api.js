const SPREADSHEET_ID = '1qgIKoJ9Pj_nS7msjVknFDjfiuz41FxIW5jFqc6aGZXA';
const FOLDER_ID = '16TIvPJuNhu3kvVXhfrhmIScwQrnpSJip';

/**
 * JSON出力用（シンプル版）
 * ContentServiceではsetHeaderが使えないので、CORS設定は不要。
 */
function createJSONResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * OPTIONSリクエスト対応（fetchのプリフライト）
 */
function doOptions(e) {
  return ContentService.createTextOutput('');
}

/**
 * GETリクエスト処理
 */
function doGet(e) {
  const path = e.parameter.path || ''; // パラメータが空でも安全に処理
  try {
    if (path === 'activities') {
      return createJSONResponse(getActivitiesData());
    } else if (path === 'announcements') {
      return createJSONResponse(getAnnouncementsData());
    } else {
      return createJSONResponse({ error: 'Invalid path' });
    }
  } catch (error) {
    return createJSONResponse({ error: error.message });
  }
}

/**
 * POSTリクエスト処理
 */
function doPost(e) {
  // multipart/form-dataでは path が取得できない場合があるためフォールバックを追加
  const path = e.parameter.path || 'submit';
  try {
    if (path === 'submit') {
      return handleSubmission(e);
    } else {
      return createJSONResponse({ error: 'Invalid path' });
    }
  } catch (error) {
    return createJSONResponse({ error: error.message });
  }
}

/**
 * 活動報告データを取得
 */
function getActivitiesData() {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName('活動報告');
  if (!sheet) return { error: 'Sheet "活動報告" not found' };
  const data = sheet.getDataRange().getValues();
  const headers = data.shift();
  return data
    .filter(row => row.some(cell => cell !== '')) // 空行を除外
    .map(row => {
      const obj = {};
      headers.forEach((header, i) => obj[header] = row[i]);
      return obj;
    });
}

/**
 * お知らせデータを取得
 */
function getAnnouncementsData() {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName('お知らせ');
  if (!sheet) return { error: 'Sheet "お知らせ" not found' };
  const data = sheet.getDataRange().getValues();
  const headers = data.shift();
  return data
    .filter(row => row.some(cell => cell !== ''))
    .map(row => {
      const obj = {};
      headers.forEach((header, i) => obj[header] = row[i]);
      return obj;
    });
}

/**
 * 提出物処理
 */
function handleSubmission(e) {
  try {
    if (!e.parameter.file) {
      return createJSONResponse({ error: 'No file uploaded' });
    }

    const fileBlob = Utilities.newBlob(
      Utilities.base64Decode(e.parameter.file),
      e.parameter.mimeType || 'application/octet-stream',
      e.parameter.filename || 'uploaded_file'
    );

    const folder = DriveApp.getFolderById(FOLDER_ID);
    const file = folder.createFile(fileBlob);

    const submissionsSheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName('提出物');
    if (!submissionsSheet) {
      return createJSONResponse({ error: 'Sheet "提出物" not found' });
    }

    submissionsSheet.appendRow([
      new Date(),
      e.parameter.name || '',
      e.parameter.gradeClass || '',
      file.getName(),
      file.getUrl()
    ]);

    return createJSONResponse({ success: true, fileUrl: file.getUrl() });
  } catch (error) {
    return createJSONResponse({ error: error.message });
  }
}
