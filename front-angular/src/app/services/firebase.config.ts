import { initializeApp } from "firebase/app";
import { 
  getAuth, 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  signOut, 
  onAuthStateChanged,
  User 
} from "firebase/auth";
import { 
  getFirestore, 
  collection, 
  doc, 
  setDoc, 
  getDocs, 
  getDoc,
  deleteDoc,
  query, 
  where 
} from "firebase/firestore";

// Configuration Firebase récupérée depuis la console
export const firebaseConfig = {
  apiKey: "AIzaSyAFJ7ZOfa84G22J6d94FT_tKUvcRcs3tTg",
  authDomain: "ocr-manuscrit-aa019.firebaseapp.com",
  projectId: "ocr-manuscrit-aa019",
  storageBucket: "ocr-manuscrit-aa019.firebasestorage.app",
  messagingSenderId: "857474923906",
  appId: "1:857474923906:web:e618edee05ad933ee9e39b",
  measurementId: "G-TB2EE10FEN"
};

// Initialisation unique
export const firebaseApp = initializeApp(firebaseConfig);
export const auth = getAuth(firebaseApp);
export const db = getFirestore(firebaseApp);
