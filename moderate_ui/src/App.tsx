import {
  Box,
  ColorScheme,
  ColorSchemeProvider,
  Container,
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
  useNotificationProvider,
} from "@refinedev/mantine";
import routerBindings, {
  DocumentTitleHandler,
  NavigateToResource,
  UnsavedChangesNotifier,
} from "@refinedev/react-router-v6";
import { IconBox } from "@tabler/icons-react";
import axios from "axios";
import { useTranslation } from "react-i18next";
import { BrowserRouter, Outlet, Route, Routes } from "react-router-dom";
import { getBaseApiUrl } from "./api/utils";
import { buildKeycloakAuthProvider } from "./auth-provider/keycloak";
import { HeaderMegaMenu } from "./components/HeaderMegaMenu";
import { Homepage } from "./pages/Homepage";
import { AssetObjectExploratoryDashboard } from "./pages/asset-objects/ExploratoryDashboard";
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

  const TokenRouteParent: React.FC = () => {
    const { keycloak } = useKeycloak();
    const { token } = keycloak;

    if (token) {
      Object.assign(axios.defaults.headers.common, {
        Authorization: `Bearer ${token}`,
      });
    }

    return <Outlet />;
  };

  const AuthenticatedGuardRouteParent: React.FC = () => {
    return (
      <Authenticated key="authenticated-outer" fallback={<Outlet />}>
        <NavigateToResource />
      </Authenticated>
    );
  };

  const HeaderContainerRouteParent: React.FC<{
    containerProps?: React.ComponentProps<typeof Container>;
  }> = ({ containerProps }) => {
    return (
      <>
        <Box mb="md">
          <HeaderMegaMenu />
        </Box>
        <Container size="xl" {...containerProps}>
          <Outlet />
        </Container>
      </>
    );
  };

  const HeaderFluidContainerRouteParent: React.FC = () => {
    return <HeaderContainerRouteParent containerProps={{ fluid: true }} />;
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
                  notificationProvider={useNotificationProvider}
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
                    <Route element={<TokenRouteParent />}>
                      <Route element={<HeaderContainerRouteParent />}>
                        <Route path="/assets">
                          <Route path="create" element={<AssetCreate />} />
                          <Route path="edit/:id" element={<AssetEdit />} />
                          <Route path="show/:id" element={<AssetShow />} />
                        </Route>
                      </Route>
                      <Route element={<HeaderFluidContainerRouteParent />}>
                        <Route path="" element={<Homepage />} />
                        <Route path="/assets">
                          <Route index element={<AssetList />} />
                          <Route path=":id/objects">
                            <Route
                              path="show/:objectId"
                              element={<AssetObjectShow />}
                            />
                            <Route
                              path="explore/:objectId"
                              element={<AssetObjectExploratoryDashboard />}
                            />
                          </Route>
                        </Route>
                      </Route>
                      <Route element={<AuthenticatedGuardRouteParent />}>
                        <Route path="/login" element={<Login />} />
                      </Route>
                      <Route path="*" element={<ErrorComponent />} />
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
