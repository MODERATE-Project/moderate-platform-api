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
import { Authenticated, Refine } from "@refinedev/core";
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
  useDocumentTitle,
} from "@refinedev/react-router-v6";
import { IconBox } from "@tabler/icons-react";
import axios from "axios";
import { useTranslation } from "react-i18next";
import { BrowserRouter, Outlet, Route, Routes } from "react-router-dom";
import { getBaseApiUrl } from "./api/utils";
import { buildKeycloakAuthProvider } from "./auth-provider/keycloak";
import { useRefreshToken } from "./auth-provider/utils";
import { DevelopmentBanner } from "./components/DevelopmentBanner";
import { FooterLinks } from "./components/FooterLinks";
import { GlobalErrorBoundary } from "./components/GlobalErrorBoundary";
import { GlobalErrorListener } from "./components/GlobalErrorListener";
import { HeaderMegaMenu } from "./components/HeaderMegaMenu";
import { Catalogue } from "./pages/Catalogue";
import { Homepage } from "./pages/Homepage";
import { AssetObjectExploratoryDashboard } from "./pages/asset-objects/ExploratoryDashboard";
import { AssetObjectShow } from "./pages/asset-objects/Show";
import { AssetCreate, AssetEdit, AssetList, AssetShow } from "./pages/assets";
import { Login } from "./pages/login";
import { NotebookExploratory } from "./pages/notebooks/Exploratory";
import { MatrixProfileWorkflow } from "./pages/notebooks/MatrixProfile";
import { NotebookSyntheticLoad } from "./pages/notebooks/SyntheticLoad";
import { dataProvider } from "./rest-data-provider";
import { ResourceNames } from "./types";

function App() {
  const [colorScheme, setColorScheme] = useLocalStorage<ColorScheme>({
    key: "mantine-color-scheme",
    defaultValue: "light",
    getInitialValueInEffect: true,
  });

  const { keycloak, initialized } = useKeycloak();
  const { t, i18n } = useTranslation();
  useRefreshToken();

  const toggleColorScheme = (value?: ColorScheme) =>
    setColorScheme(value || (colorScheme === "dark" ? "light" : "dark"));

  useDocumentTitle("MODERATE Platform");

  if (!initialized) {
    return <div>Loading...</div>;
  }

  const authProvider = buildKeycloakAuthProvider({ keycloak });

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

    return (
      <>
        <DevelopmentBanner />
        <Outlet />
      </>
    );
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
        <Container
          size="xl"
          {...containerProps}
          style={{
            minHeight: "54vh",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Outlet />
        </Container>
        <FooterLinks
          data={[
            {
              title: "About MODERATE",
              links: [
                {
                  label: "In a nutshell",
                  link: "https://moderate-project.eu/in-a-nutshell/",
                },
                {
                  label: "News",
                  link: "https://moderate-project.eu/news/",
                },
                {
                  label: "Contact",
                  link: "https://moderate-project.eu/contact/",
                },
              ],
            },
          ]}
        />
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
              <GlobalErrorBoundary>
                <GlobalErrorListener />
                <DevtoolsProvider>
                  <Refine
                    dataProvider={dataProvider(getBaseApiUrl())}
                    notificationProvider={useNotificationProvider}
                    routerProvider={routerBindings}
                    authProvider={authProvider}
                    i18nProvider={i18nProvider}
                    resources={[
                      {
                        name: ResourceNames.ASSET,
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
                      projectId: "moderate-platform-ui",
                      title: {
                        text: "MODERATE Platform",
                      },
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
                          <Route path="/workflows">
                            <Route
                              path="exploratory"
                              element={<NotebookExploratory />}
                            />
                            <Route
                              path="synthetic-load"
                              element={<NotebookSyntheticLoad />}
                            />
                            <Route
                              path="matrix-profile"
                              element={<MatrixProfileWorkflow />}
                            />
                          </Route>
                          <Route path="/catalogue" element={<Catalogue />} />
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
              </GlobalErrorBoundary>
            </NotificationsProvider>
          </MantineProvider>
        </ColorSchemeProvider>
      </RefineKbarProvider>
    </BrowserRouter>
  );
}

export default App;
