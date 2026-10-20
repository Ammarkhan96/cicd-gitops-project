{{- define "gitops-demo.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "gitops-demo.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "gitops-demo.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "gitops-demo.labels" -}}
app.kubernetes.io/name: {{ include "gitops-demo.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end -}}
