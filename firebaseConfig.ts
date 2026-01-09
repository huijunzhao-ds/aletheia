import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const env = import.meta.env as {
    VITE_FIREBASE_API_KEY: string;
    VITE_FIREBASE_AUTH_DOMAIN: string;
    VITE_FIREBASE_PROJECT_ID: string;
    VITE_FIREBASE_STORAGE_BUCKET: string;
    VITE_FIREBASE_MESSAGING_SENDER_ID: string;
    VITE_FIREBASE_APP_ID: string;
};

function getEnvVar(key: keyof typeof env): string {
    const value = env[key];
    if (typeof value !== "string" || value.trim() === "") {
        throw new Error(
            `Missing or empty Firebase configuration value for "${key}". ` +
            `Ensure the corresponding Vite environment variable is set.`
        );
    }
    return value;
}

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
