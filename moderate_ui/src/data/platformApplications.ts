import {
  IconBuildingCommunity,
  IconCertificate,
  IconChartDots,
  IconChartInfographic,
  IconMap2,
  IconNetwork,
  IconSolarPanel,
  IconTools,
} from "@tabler/icons-react";
import type React from "react";

export interface PlatformApplication {
  id: string;
  titleKey: string;
  defaultTitle: string;
  descKey: string;
  defaultDesc: string;
  url: string;
  icon: React.ComponentType<{
    size?: number | string;
    color?: string;
    stroke?: number | string;
  }>;
  iconColor: string;
  categoryKey: string;
  defaultCategory: string;
}

export const platformApplications: PlatformApplication[] = [
  {
    id: "brickllm",
    titleKey: "home.application.brickllm.title",
    defaultTitle: "BrickLLM",
    descKey: "home.application.brickllm.desc",
    defaultDesc:
      "Generate BrickSchema RDF building descriptions with LLM-assisted interoperability workflows.",
    url: "https://brick.staging.moderate.cloud/brickllm/",
    icon: IconNetwork,
    iconColor: "indigo",
    categoryKey: "home.application.category.interoperability",
    defaultCategory: "Interoperability",
  },
  {
    id: "building-benchmarking",
    titleKey: "home.application.buildingBenchmarking.title",
    defaultTitle: "Building Benchmarking & Analytics",
    descKey: "home.application.buildingBenchmarking.desc",
    defaultDesc:
      "Compare building KPIs, detect anomalies, support M&V, and use AI-assisted metadata workflows.",
    url: "https://tools.eeb.eurac.edu/building_benchmarking/",
    icon: IconChartInfographic,
    iconColor: "blue",
    categoryKey: "home.application.category.benchmarking",
    defaultCategory: "Benchmarking",
  },
  {
    id: "encome",
    titleKey: "home.application.encome.title",
    defaultTitle: "ENCOME ECM Tool",
    descKey: "home.application.encome.desc",
    defaultDesc:
      "Assess energy conservation measures and renovation scenarios using EN ISO-based calculations.",
    url: "https://tools.eeb.eurac.edu/encome/",
    icon: IconTools,
    iconColor: "orange",
    categoryKey: "home.application.category.ecm",
    defaultCategory: "ECM",
  },
  {
    id: "geo-clustering",
    titleKey: "home.application.geoClustering.title",
    defaultTitle: "Geo-clustering",
    descKey: "home.application.geoClustering.desc",
    defaultDesc:
      "Cluster EPC and building records by geospatial and physical features with sensitivity analysis.",
    url: "https://tools.eeb.eurac.edu/epc_clustering/piemonte/",
    icon: IconMap2,
    iconColor: "green",
    categoryKey: "home.application.category.geoClustering",
    defaultCategory: "Geo-clustering",
  },
  {
    id: "solar-cadastre",
    titleKey: "home.application.solarCadastre.title",
    defaultTitle: "Solar Cadastre",
    descKey: "home.application.solarCadastre.desc",
    defaultDesc:
      "Explore building solar potential and PV performance through map-based cadastre data.",
    url: "https://solar.staging.moderate.cloud/",
    icon: IconSolarPanel,
    iconColor: "yellow",
    categoryKey: "home.application.category.solar",
    defaultCategory: "Solar",
  },
  {
    id: "lec-assessment",
    titleKey: "home.application.lecAssessment.title",
    defaultTitle: "LEC Assessment Tool",
    descKey: "home.application.lecAssessment.desc",
    defaultDesc:
      "Identify promising Local Energy Community areas using building, energy, and cadastral data.",
    url: "https://lec.staging.moderate.cloud/",
    icon: IconBuildingCommunity,
    iconColor: "teal",
    categoryKey: "home.application.category.lec",
    defaultCategory: "LEC",
  },
  {
    id: "epc-quality-check",
    titleKey: "home.application.epcQualityCheck.title",
    defaultTitle: "EPC Quality Check",
    descKey: "home.application.epcQualityCheck.desc",
    defaultDesc:
      "Validate EPC XML files against quality rules and produce clear reporting feedback.",
    url: "http://moderate.five.es:55000/",
    icon: IconCertificate,
    iconColor: "red",
    categoryKey: "home.application.category.quality",
    defaultCategory: "Quality",
  },
  {
    id: "timeseries-benchmarking",
    titleKey: "home.application.timeseriesBenchmarking.title",
    defaultTitle: "Timeseries Energy Benchmarking",
    descKey: "home.application.timeseriesBenchmarking.desc",
    defaultDesc:
      "Benchmark hourly energy use against peers with preprocessing, KPIs, and anomaly indicators.",
    url: "https://timeseries.staging.moderate.cloud/",
    icon: IconChartDots,
    iconColor: "grape",
    categoryKey: "home.application.category.timeseries",
    defaultCategory: "Timeseries",
  },
];
