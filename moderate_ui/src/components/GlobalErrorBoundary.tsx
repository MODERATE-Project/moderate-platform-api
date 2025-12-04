import {
  Box,
  Button,
  Code,
  Container,
  Group,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertTriangle } from "@tabler/icons-react";
import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Global Error Boundary to catch React render errors.
 * This must be a Class Component as hooks for error boundaries do not exist yet.
 */
export class GlobalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <Container size="md" py="xl">
          <Paper p="xl" radius="md" withBorder shadow="sm">
            <Stack align="center" spacing="lg">
              <IconAlertTriangle size={50} color="red" />
              <Title order={2} align="center">
                Something went wrong
              </Title>
              <Text color="dimmed" align="center" size="lg">
                The application encountered an unexpected error.
              </Text>

              <Group position="center">
                <Button onClick={this.handleReset} size="md" variant="light">
                  Reload Application
                </Button>
              </Group>

              {this.state.error && (
                <Box w="100%" mt="md">
                  <Text weight={500} mb="xs">
                    Error Details:
                  </Text>
                  <Code block color="red">
                    {this.state.error.toString()}
                  </Code>
                </Box>
              )}
            </Stack>
          </Paper>
        </Container>
      );
    }

    return this.props.children;
  }
}
