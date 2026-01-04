import * as Google from 'expo-auth-session/providers/google';
import * as WebBrowser from 'expo-web-browser';

WebBrowser.maybeCompleteAuthSession();

// Google OAuth Client IDs
const GOOGLE_WEB_CLIENT_ID = '900765924270-vb5bemr9n2gt40sr4bcprgfg16ma2cbh.apps.googleusercontent.com';
const GOOGLE_IOS_CLIENT_ID = '900765924270-a7ph2bu5f4f61r2ljfpv4ga3qjfq0425.apps.googleusercontent.com';

export function useGoogleAuth() {
  const [request, response, promptAsync] = Google.useIdTokenAuthRequest({
    clientId: GOOGLE_WEB_CLIENT_ID,
    iosClientId: GOOGLE_IOS_CLIENT_ID,
  });

  const isConfigured = true;

  return {
    request,
    response,
    promptAsync,
    isConfigured,
  };
}
