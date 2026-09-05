"""Bilingual copy for deliberate, read-only roster sharing."""

MESSAGES = {
    "access_summary_title": {"zh-HK": "目前存取狀態", "en": "Current access status"},
    "access_summary_identity": {"zh-HK": "身份", "en": "Identity"},
    "access_summary_session": {"zh-HK": "工作階段", "en": "Session"},
    "access_summary_security": {"zh-HK": "權限狀態", "en": "Permission status"},
    "access_summary_active": {"zh-HK": "目前工作階段有效", "en": "Current session active"},
    "access_summary_expires_at": {"zh-HK": "到期：{value}", "en": "Expires: {value}"},
    "access_summary_capabilities": {"zh-HK": "此身份具備 {count} 項權限；操作時仍會重新驗證。", "en": "This identity has {count} capabilities; each operation is rechecked."},
    "access_technical_controls": {"zh-HK": "技術詳情與分享管理", "en": "Technical details and share management"},
    "access_control": {
        "zh-HK": "存取控制台",
        "en": "Access control",
    },
    "access_control_intro": {
        "zh-HK": "所有人使用同一個網站：未登入時只可查看你分享的已發布週表；管理員登入並通過身份核實後，才會解鎖完整工作台。",
        "en": "Everyone uses the same website. Signed-out visitors can view only published rosters you share; the full workspace unlocks only after the administrator signs in and passes identity verification.",
    },
    "access_permission_model_title": {
        "zh-HK": "兩級權限模型",
        "en": "Two-level permission model",
    },
    "access_operator_title": {
        "zh-HK": "OP・可編輯",
        "en": "OP · Can edit",
    },
    "access_operator_body": {
        "zh-HK": "在同一個網站點按「管理員登入」，經 Cloudflare Access 核對指定帳戶後，才可生成、發布、調整、審計、備份及還原。系統不保存自製密碼。",
        "en": "Choose Admin sign-in on the same website. Generate, publish, adjust, audit, back up, and restore only after Cloudflare Access verifies the named account. The system stores no homemade password.",
    },
    "access_operator_local": {
        "zh-HK": "同一個正式網站",
        "en": "One official website",
    },
    "access_operator_remote": {
        "zh-HK": "主機維護後備",
        "en": "Host maintenance fallback",
    },
    "access_operator_warp_note": {
        "zh-HK": "日常只派發上方同一個正式網址。本機地址只供主機故障排查，不是另一個日常入口；登出後會立即回到訪客唯讀模式。",
        "en": "Distribute only the one official address above. The local address is for host troubleshooting, not a second everyday entry; signing out returns the site to guest read-only mode.",
    },
    "access_viewer_title": {
        "zh-HK": "Viewer・僅查看",
        "en": "Viewer · View only",
    },
    "access_viewer_body": {
        "zh-HK": "收件者在一般瀏覽器開啟同一個網站，不需安裝或登入；只有持有完整週表連結時才可解密查看你明確分享的已發布安排。",
        "en": "Recipients open the same website in a normal browser without installing or signing in. A complete roster link is required to decrypt only the published schedule you explicitly shared.",
    },
    "access_admin_mode": {
        "zh-HK": "管理員模式",
        "en": "Administrator mode",
    },
    "access_admin_signed_in": {
        "zh-HK": "已安全登入",
        "en": "Securely signed in",
    },
    "access_admin_logout": {
        "zh-HK": "登出",
        "en": "Sign out",
    },
    "access_guest_mode": {
        "zh-HK": "訪客示範模式",
        "en": "Guest demo mode",
    },
    "access_guest_signed_in": {
        "zh-HK": "DEMO・臨時工作區",
        "en": "DEMO · Temporary workspace",
    },
    "access_guest_mode_body": {
        "zh-HK": "你正在使用只含虛構中文姓名的臨時工作區；可完整試用排班流程，但資料不會寫入正式名單、帳本、備份或外部服務。",
        "en": "You are using a temporary workspace containing fictional Chinese names only. You can try the full roster flow, but nothing is written to the official directory, ledger, backups, or external services.",
    },
    "access_restricted_title": {
        "zh-HK": "RESTRICTED・訪客模式不會執行此操作",
        "en": "RESTRICTED · Not executed in guest mode",
    },
    "access_restricted_body": {
        "zh-HK": "這項功能涉及上載、外部連接或永久資料。你仍可使用已核准的虛構資料完成其餘示範流程。",
        "en": "This feature uses uploads, an external connection, or permanent data. Continue the demonstration with the approved fictional dataset.",
    },
    "access_select_roster": {
        "zh-HK": "選擇已發布週表",
        "en": "Choose a published roster",
    },
    "access_no_published_roster": {
        "zh-HK": "尚未有已發布週表；先生成、核對及發布，才可建立 Viewer 連結。",
        "en": "There is no published roster yet. Generate, review, and publish one before creating a Viewer link.",
    },
    "access_manage_links": {
        "zh-HK": "載入及管理有效連結",
        "en": "Load and manage active links",
    },
    "access_open_console": {
        "zh-HK": "開啟存取控制台",
        "en": "Open access control",
    },
    "access_permission_label": {
        "zh-HK": "權限：{value}",
        "en": "Permission: {value}",
    },
    "access_share_id": {
        "zh-HK": "連結識別碼：{value}",
        "en": "Link ID: {value}",
    },
    "access_week_label": {
        "zh-HK": "週次：{value}",
        "en": "Week: {value}",
    },
    "access_copy_address": {
        "zh-HK": "複製入口地址",
        "en": "Copy entry address",
    },
    "public_share_title": {
        "zh-HK": "瀏覽器直達查看連結",
        "en": "Browser-direct viewing link",
    },
    "public_share_intro": {
        "zh-HK": "為已發布值班表建立一條只讀連結。收件者直接在瀏覽器開啟即可，不會進入名單、請假、公平帳本、備份或設定。",
        "en": "Create a read-only link for this published roster. Recipients open it directly in a browser and cannot enter the directory, leave records, fairness ledger, backups, or settings.",
    },
    "public_share_not_configured": {
        "zh-HK": "公開查看服務尚未完成設定；正式值班系統仍可照常使用。",
        "en": "The public viewer has not been configured yet; the official roster system remains fully available.",
    },
    "public_share_create": {
        "zh-HK": "建立唯讀查看連結",
        "en": "Create read-only viewing link",
    },
    "public_share_confirm_title": {
        "zh-HK": "確認建立對外查看連結",
        "en": "Confirm external viewing link",
    },
    "public_share_confirm_body": {
        "zh-HK": "連結只包含週次、日期、崗位、當值時間及中文姓名；不包含請假原因、班別、角色、公平點數、審計、備份或日誌。任何取得完整連結的人都可在到期或撤銷前查看。",
        "en": "The link contains only the roster week, dates, duty posts, duty times, and Chinese names. It excludes leave reasons, classes, roles, fairness points, audit records, backups, and logs. Anyone with the complete link can view it until it expires or is revoked.",
    },
    "public_share_confirm_action": {
        "zh-HK": "確認並建立連結",
        "en": "Confirm and create link",
    },
    "public_share_progress_title": {
        "zh-HK": "正在建立安全查看連結",
        "en": "Creating secure viewing link",
    },
    "public_share_progress_working": {
        "zh-HK": "正在本機整理及加密已發布值班表，然後傳送密文。",
        "en": "Preparing and encrypting the published roster locally, then sending ciphertext.",
    },
    "public_share_manage_progress_title": {
        "zh-HK": "正在載入查看權限",
        "en": "Loading viewing access",
    },
    "public_share_manage_progress_working": {
        "zh-HK": "正在核對目前有效及可撤銷的唯讀連結。",
        "en": "Checking the currently active and revocable read-only links.",
    },
    "public_share_revoke_progress_title": {
        "zh-HK": "正在撤銷查看連結",
        "en": "Revoking viewing link",
    },
    "public_share_revoke_progress_working": {
        "zh-HK": "正在移除這條唯讀連結的雲端密文。",
        "en": "Removing this read-only link's encrypted cloud record.",
    },
    "public_share_created_title": {
        "zh-HK": "查看連結已建立",
        "en": "Viewing link created",
    },
    "public_share_created_body": {
        "zh-HK": "請現在複製連結；解密鑰匙只存在於完整連結，系統不會另行保存或再次顯示。",
        "en": "Copy the link now. Its decryption key exists only in the complete link and is not stored or shown again by the system.",
    },
    "public_share_link_label": {
        "zh-HK": "唯讀查看連結",
        "en": "Read-only viewing link",
    },
    "public_share_copy": {
        "zh-HK": "複製連結",
        "en": "Copy link",
    },
    "public_share_copied": {
        "zh-HK": "連結已複製。",
        "en": "Link copied.",
    },
    "public_share_expiry": {
        "zh-HK": "到期時間：{value}",
        "en": "Expires: {value}",
    },
    "public_share_active_title": {
        "zh-HK": "目前有效的查看連結",
        "en": "Active viewing links",
    },
    "public_share_active_empty": {
        "zh-HK": "這一週目前沒有有效的查看連結。",
        "en": "There is currently no active viewing link for this week.",
    },
    "public_share_pending_title": {
        "zh-HK": "{count} 條舊 Viewer 連結仍待撤銷",
        "en": "{count} old Viewer link(s) still await revocation",
    },
    "public_share_pending_body": {
        "zh-HK": "正式值班變更已經提交；不要重複提交值班變更。這裡只會安全重試移除舊連結的雲端密文。",
        "en": "The official roster change is already committed; do not resubmit the roster change. This action safely retries only removal of the old links' cloud ciphertext.",
    },
    "public_share_pending_retry": {
        "zh-HK": "重試待完成撤銷",
        "en": "Retry pending revocations",
    },
    "public_share_pending_cleared": {
        "zh-HK": "待完成的舊 Viewer 連結已撤銷。",
        "en": "The pending old Viewer links were revoked.",
    },
    "public_share_pending_partial": {
        "zh-HK": "仍有 {count} 條舊 Viewer 連結待撤銷；值班變更毋須重做。",
        "en": "{count} old Viewer link(s) still await revocation; the roster change does not need to be repeated.",
    },
    "public_share_revoke": {
        "zh-HK": "撤銷",
        "en": "Revoke",
    },
    "public_share_revoke_confirm_title": {
        "zh-HK": "撤銷這條查看連結？",
        "en": "Revoke this viewing link?",
    },
    "public_share_revoke_confirm_body": {
        "zh-HK": "撤銷後，原有完整連結將不能再載入值班表；Cloudflare 邊緣快取同步最多可能需要約一分鐘。",
        "en": "After revocation, the existing complete link can no longer load the roster. Cloudflare edge propagation can take about one minute.",
    },
    "public_share_revoked": {
        "zh-HK": "查看連結已撤銷。",
        "en": "Viewing link revoked.",
    },
    "public_share_error": {
        "zh-HK": "未能完成查看連結操作；正式值班表沒有改動。",
        "en": "The viewing-link operation could not be completed. The official roster was not changed.",
    },
}
