function doPost(e) {
  try {
    // 1. 解析來自 Streamlit Python 的 JSON 數據 Payload
    var data = JSON.parse(e.postData.contents);
    
    // 取得目前綁定的試算表 (確保有名為 'Basic Info' 的工作表，否則用第一頁)
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Basic Info");
    if (!sheet) {
       sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
    }
    
    // ==========================================
    // 📁 第一部分：處理 Google Drive 資料夾與圖片
    // ==========================================
    
    // 建立專屬資料夾 (命名格式：專案名稱_年月日時分秒)
    var projectName = data.project_name ? data.project_name : "Untitled_Project";
    var timeString = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyyMMdd_HHmmss");
    var folderName = projectName + "_" + timeString;
    var folder = DriveApp.createFolder(folderName);
    var folderUrl = folder.getUrl(); // 取得資料夾連結，稍後放入 Sheet
    
    // 儲存活動相片 (P1 到 P8) -> 轉為 JPEG
    if (data.images && data.images.length > 0) {
      for (var i = 0; i < data.images.length; i++) {
        var imgBase64 = data.images[i];
        if (imgBase64) {
          var imgBlob = Utilities.base64Decode(imgBase64);
          var imgFile = Utilities.newBlob(imgBlob, 'image/jpeg', 'Photo_' + (i + 1) + '.jpg');
          folder.createFile(imgFile);
        }
      }
    }
    
    // 儲存黑色 Logo -> 轉為保留透明底的 PNG
    if (data.logo_black && data.logo_black !== "") {
      var blobBlack = Utilities.base64Decode(data.logo_black);
      var logoBlackFile = Utilities.newBlob(blobBlack, 'image/png', 'Client_Logo_Black.png');
      folder.createFile(logoBlackFile);
    }
    
    // 儲存白色 Logo -> 轉為保留透明底的 PNG
    if (data.logo_white && data.logo_white !== "") {
      var blobWhite = Utilities.base64Decode(data.logo_white);
      var logoWhiteFile = Utilities.newBlob(blobWhite, 'image/png', 'Client_Logo_White.png');
      folder.createFile(logoWhiteFile);
    }

    // ==========================================
    // 🧠 第二部分：處理 AI 文案提取 (防漏空機制)
    // ==========================================
    var ai = data.ai_content || {};
    
    // 智能提取 AI 文本的過濾器
    function getAiText(platformData) {
      if (!platformData) return "";
      if (typeof platformData === 'string') return platformData;
      if (platformData.content) return platformData.content;
      if (platformData.text) return platformData.text;
      
      // 針對 Google Slide 的 Hook-Shift-Proof 特殊結構
      if (platformData.hook || platformData.shift || platformData.proof) {
        var slideText = "";
        if (platformData.hook) slideText += "【Hook】\n" + platformData.hook + "\n\n";
        if (platformData.shift) slideText += "【Shift】\n" + platformData.shift + "\n\n";
        if (platformData.proof) slideText += "【Proof】\n" + platformData.proof;
        return slideText.trim();
      }
      
      // 針對 Website 三語的 Title + Content 結構
      if (platformData.title && platformData.content) {
        return "【" + platformData.title + "】\n" + platformData.content;
      }
      
      // 如果結構意料之外，直接轉為文字保留
      return JSON.stringify(platformData, null, 2);
    }
    
    var website = ai["6_website"] || {};
    
    // ==========================================
    // 📝 第三部分：寫入 Google Sheet
    // ==========================================
    
    // 將數據映射到對應的 Column 陣列 (A 到 V 欄)
    var rowData = [
      data.timestamp || "",                     // A: 提交時間
      data.client_name || "",                   // B: Client
      data.project_name || "",                  // C: Project
      data.event_date || "",                    // D: Date
      data.venue || "",                         // E: Venue
      data.category_who || "",                  // F: Category (Client)
      data.category_what || "",                 // G: What we do
      data.scope_of_work || "",                 // H: Scope of Work
      data.youtube_link || "",                  // I: YouTube Link
      data.open_question || "",                 // J: Open Question (概念特別之處)
      data.challenge || "",                     // K: Boring Challenge
      data.solution || "",                      // L: Creative Solution
      
      // 六大平台文案
      getAiText(ai["1_google_slide"]),          // M: Google Slide
      getAiText(ai["5_linkedin_post"]),         // N: LinkedIn
      getAiText(ai["2_facebook_post"]),         // O: Facebook
      getAiText(ai["3_threads_post"]),          // P: Threads
      getAiText(ai["4_instagram_post"]),        // Q: Instagram
      
      // Website 三語
      getAiText(website["en"]),                 // R: Web EN
      getAiText(website["tc"]),                 // S: Web TC
      getAiText(website["jp"]),                 // T: Web JP
      
      "Synced Success",                         // U: 同步狀態
      folderUrl                                 // V: 📂 自動生成的 Google Drive 資料夾連結
    ];
    
    // 寫入新的一行
    sheet.appendRow(rowData);
    
    // 回傳成功訊號給 Python
    return ContentService.createTextOutput(JSON.stringify({
      "status": "success", 
      "message": "Row added and folder created",
      "folder_url": folderUrl
    })).setMimeType(ContentService.MimeType.JSON);
      
  } catch(error) {
    // 錯誤處理
    return ContentService.createTextOutput(JSON.stringify({
      "status": "error", 
      "message": error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
