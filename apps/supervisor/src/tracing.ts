import { resourceFromAttributes } from "@opentelemetry/resources";
import { NodeTracerProvider, SimpleSpanProcessor } from "@opentelemetry/sdk-trace-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-proto";
import { registerInstrumentations } from "@opentelemetry/instrumentation";
import { OpenAIInstrumentation } from "@traceloop/instrumentation-openai";

const globalKey = Symbol.for("shopify.blog.supervisor.tracing");
const globalState = globalThis as typeof globalThis & { [globalKey]?: boolean };

const tracingDisabled = process.env.ENABLE_TRACING === "false";

if (!tracingDisabled && !globalState[globalKey]) {
  const serviceName = process.env.TRACING_SERVICE_NAME || "shopify-blog-supervisor";
  const exporterEndpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT || "http://localhost:4318/v1/traces";

  const exporter = new OTLPTraceExporter({ url: exporterEndpoint });
  const provider = new NodeTracerProvider({
    resource: resourceFromAttributes({
      "service.name": serviceName,
    }),
    spanProcessors: [new SimpleSpanProcessor(exporter)],
  });
  provider.register();

  registerInstrumentations({
    instrumentations: [new OpenAIInstrumentation()],
  });

  globalState[globalKey] = true;
}
