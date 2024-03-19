import {
  ColorScheme,
  ColorSchemeProvider,
  Global,
  MantineProvider,
} from "@mantine/core";
import { useLocalStorage } from "@mantine/hooks";
import { NotificationsProvider } from "@mantine/notifications";
import { useKeycloak } from "@react-keycloak/web";
import { AuthBindings, Authenticated, Refine } from "@refinedev/core";
import { DevtoolsPanel, DevtoolsProvider } from "@refinedev/devtools";
import { RefineKbar, RefineKbarProvider } from "@refinedev/kbar";
import {
  ErrorComponent,
  RefineThemes,
  ThemedLayoutV2,
  ThemedSiderV2,
  notificationProvider,
} from "@refinedev/mantine";
import routerBindings, {
  CatchAllNavigate,
  DocumentTitleHandler,
  NavigateToResource,
  UnsavedChangesNotifier,
} from "@refinedev/react-router-v6";
import { IconBox } from "@tabler/icons";
import { useTranslation } from "react-i18next";
import { BrowserRouter, Outlet, Route, Routes } from "react-router-dom";
import { getBaseApiUrl } from "./api/utils";
import { buildKeycloakAuthProvider } from "./auth-provider/keycloak";
import { Header } from "./components/header";
import { AssetObjectShow } from "./pages/asset-objects/Show";
import { AssetCreate, AssetEdit, AssetList, AssetShow } from "./pages/assets";
import { Login } from "./pages/login";
import { dataProvider } from "./rest-data-provider";

function App() {
  const [colorScheme, setColorScheme] = useLocalStorage<ColorScheme>({
    key: "mantine-color-scheme",
    defaultValue: "light",
    getInitialValueInEffect: true,
  });

  const { keycloak, initialized } = useKeycloak();
  const { t, i18n } = useTranslation();

  const toggleColorScheme = (value?: ColorScheme) =>
    setColorScheme(value || (colorScheme === "dark" ? "light" : "dark"));

  if (!initialized) {
    return <div>Loading...</div>;
  }

  const authProvider: AuthBindings = buildKeycloakAuthProvider({ keycloak });

  const i18nProvider = {
    translate: (key: string, params: object) => t(key, params),
    changeLocale: (lang: string) => i18n.changeLanguage(lang),
    getLocale: () => i18n.language,
  };

  return (
    <BrowserRouter>
      <RefineKbarProvider>
        <ColorSchemeProvider
          colorScheme={colorScheme}
          toggleColorScheme={toggleColorScheme}
        >
          <MantineProvider
            theme={{ ...RefineThemes.Purple, colorScheme: colorScheme }}
            withNormalizeCSS
            withGlobalStyles
          >
            <Global styles={{ body: { WebkitFontSmoothing: "auto" } }} />
            <NotificationsProvider position="top-right">
              <DevtoolsProvider>
                <Refine
                  dataProvider={dataProvider(getBaseApiUrl())}
                  notificationProvider={notificationProvider}
                  routerProvider={routerBindings}
                  authProvider={authProvider}
                  i18nProvider={i18nProvider}
                  resources={[
                    {
                      name: "asset",
                      list: "/assets",
                      create: "/assets/create",
                      edit: "/assets/edit/:id",
                      show: "/assets/show/:id",
                      meta: {
                        canDelete: true,
                        icon: <IconBox />,
                      },
                    },
                  ]}
                  options={{
                    syncWithLocation: true,
                    warnWhenUnsavedChanges: true,
                    useNewQueryKeys: true,
                    projectId: "jjTjGn-5AuAqE-qsmr54",
                  }}
                >
                  <Routes>
                    <Route
                      element={
                        <Authenticated
                          key="authenticated-inner"
                          fallback={<CatchAllNavigate to="/login" />}
                        >
                          <ThemedLayoutV2
                            Sider={() => (
                              <ThemedSiderV2
                                Title={({ collapsed }) => (
                                  <img
                                    src={
                                      collapsed
                                        ? "/images/moderate-logo-collapsed.png"
                                        : "/images/moderate-logo-wide.png"
                                    }
                                    style={{
                                      maxWidth: "90%",
                                      maxHeight: "80%",
                                    }}
                                  />
                                )}
                              />
                            )}
                            Header={() => <Header sticky />}
                          >
                            <Outlet />
                          </ThemedLayoutV2>
                        </Authenticated>
                      }
                    >
                      <Route
                        index
                        element={<NavigateToResource resource="assets" />}
                      />
                      <Route path="/assets">
                        <Route index element={<AssetList />} />
                        <Route path="create" element={<AssetCreate />} />
                        <Route path="edit/:id" element={<AssetEdit />} />
                        <Route path="show/:id" element={<AssetShow />} />
                        <Route path=":id/objects">
                          <Route
                            path="show/:objectId"
                            element={<AssetObjectShow />}
                          />
                        </Route>
                      </Route>
                      <Route path="*" element={<ErrorComponent />} />
                    </Route>
                    <Route
                      element={
                        <Authenticated
                          key="authenticated-outer"
                          fallback={<Outlet />}
                        >
                          <NavigateToResource />
                        </Authenticated>
                      }
                    >
                      <Route path="/login" element={<Login />} />
                    </Route>
                  </Routes>
                  <RefineKbar />
                  <UnsavedChangesNotifier />
                  <DocumentTitleHandler />
                </Refine>
                <DevtoolsPanel />
              </DevtoolsProvider>
            </NotificationsProvider>
          </MantineProvider>
        </ColorSchemeProvider>
      </RefineKbarProvider>
    </BrowserRouter>
  );
}

export default App;
