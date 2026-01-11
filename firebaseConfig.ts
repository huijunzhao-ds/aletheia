import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const env = (import.meta as any).env || {};

function getEnvVar(key: keyof typeof env): string {
    const value = env[key];
    if (typeof value !== "string" || value.trim() === "") {
        console.warn(
            `Missing or empty Firebase configuration value for "${String(key)}". ` +
            `Ensure the corresponding Vite environment variable is set during the build.`
        );
        return "";
    }
    return value;
}

export const isFirebaseConfigured = !!(
    env.VITE_FIREBASE_API_KEY &&
    env.VITE_FIREBASE_PROJECT_ID &&
    env.VITE_FIREBASE_APP_ID
);

const firebaseConfig = {
    apiKey: getEnvVar("VITE_FIREBASE_API_KEY"),
    authDomain: getEnvVar("VITE_FIREBASE_AUTH_DOMAIN"),
    projectId: getEnvVar("VITE_FIREBASE_PROJECT_ID"),
    storageBucket: getEnvVar("VITE_FIREBASE_STORAGE_BUCKET"),
    messagingSenderId: getEnvVar("VITE_FIREBASE_MESSAGING_SENDER_ID"),
    appId: getEnvVar("VITE_FIREBASE_APP_ID")
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
