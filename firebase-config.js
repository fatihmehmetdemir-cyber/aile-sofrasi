// Firebase Console > Project settings > Your apps > Web app içindeki firebaseConfig değerlerini buraya yapıştır.
// Firebase Web API anahtarı Firebase servisleri için public-by-design'dır; asıl erişim Firestore Security Rules ile korunur.
export const firebaseConfig = {
  apiKey: "BURAYA_FIREBASE_API_KEY",
  authDomain: "BURAYA_PROJECT_ID.firebaseapp.com",
  projectId: "BURAYA_PROJECT_ID",
  storageBucket: "BURAYA_PROJECT_ID.firebasestorage.app",
  messagingSenderId: "BURAYA_MESSAGING_SENDER_ID",
  appId: "BURAYA_APP_ID"
};
