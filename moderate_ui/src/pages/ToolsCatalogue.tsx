import {
  Box,
  Button,
  Card,
  Grid,
  Group,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  IconBook,
  IconBrowser,
  IconGitFork,
  IconHomeEco,
  IconTools,
} from "@tabler/icons-react";
import React from "react";
import { useTranslation } from "react-i18next";

interface ToolDetails {
  name: string;
  description: string;
  icon: React.ReactNode;
  documentationUrl?: string;
  appUrl?: string;
  gitUrl?: string;
}

const ToolCard: React.FC<ToolDetails> = ({
  name,
  description,
  icon,
  documentationUrl,
  appUrl,
  gitUrl,
}) => {
  const { t } = useTranslation();

  return (
    <Card shadow="sm" p="lg" radius="md" withBorder>
      <Grid gutter="xl">
        <Grid.Col md="content">{icon}</Grid.Col>
        <Grid.Col md="auto">
          <Stack spacing="xs">
            <Title order={3}>{name}</Title>
            <Text color="dimmed">{description}</Text>
          </Stack>
        </Grid.Col>
      </Grid>
      <Card.Section withBorder inheritPadding pt="lg" pb="lg" mt="lg">
        <Group>
          <Button
            color="primary"
            variant="light"
            leftIcon={<IconBook size="1rem" />}
            component="a"
            target="_blank"
            href={documentationUrl}
            disabled={!documentationUrl}
          >
            {t("tools.card.docs", "Documentation")}
          </Button>
          <Button
            color="primary"
            variant="light"
            leftIcon={<IconBrowser size="1rem" />}
            component="a"
            target="_blank"
            href={appUrl}
            disabled={!appUrl}
          >
            {t("tools.card.app", "Check the application")}
          </Button>
          <Button
            variant="light"
            color="cyan"
            leftIcon={<IconGitFork size="1rem" />}
            component="a"
            target="_blank"
            href={gitUrl}
            disabled={!gitUrl}
          >
            {t("tools.card.git", "Git repository")}
          </Button>
        </Group>
      </Card.Section>
    </Card>
  );
};

export const ToolsCatalogue: React.FC = () => {
  const { t } = useTranslation();

  const tools: ToolDetails[] = [
    {
      name: t("tools.lec.name", "Local Energy Communities Assessment"),
      description: t(
        "tools.lec.description",
        `Local Energy Communities (LECs) are pivotal in advancing building 
        decarbonization,fostering social cohesion, and promoting the
        integration of renewable energy sources. This tool streamlines the
        establishment of LECs by pinpointing optimal locations for their
        formation, enabling stakeholders to efficiently identify viable
        LEC sites.`
      ),
      icon: (
        <Box mr="lg">
          <IconHomeEco stroke="1.5" size="5rem" color="purple" />
        </Box>
      ),
      gitUrl:
        "https://github.com/MODERATE-Project/lec-location-assessment-tool",
      appUrl: "https://lec.moderate.cloud",
    },
  ];

  return (
    <>
      <Group mt="xl" position="left" style={{ flexWrap: "nowrap" }}>
        <Box mr="lg">
          <IconTools size={72} color="gray" />
        </Box>
        <Stack>
          <Title>{t("tools.title", "Tools and services")}</Title>
          <Text color="dimmed">
            {t(
              "tools.description",
              "Check out the applications and software services developed by the MODERATE Project"
            )}
          </Text>
        </Stack>
      </Group>
      <Stack spacing="xl" mt="xl" mb="xl">
        {tools.map((item) => (
          <ToolCard key={`tool-${item.name}`} {...item} />
        ))}
      </Stack>
    </>
  );
};
