namespace SubtitleCreator.Models;

public enum PipelineType { HebToHeb, AnyToHeb }

public enum JobStatus { Pending, Running, Completed, Failed, Cancelled }

public class SubtitleJob
{
    public string Id { get; init; } = Guid.NewGuid().ToString();
    public string VideoPath { get; init; } = string.Empty;
    public PipelineType Pipeline { get; init; } = PipelineType.HebToHeb;
    public JobStatus Status { get; set; } = JobStatus.Pending;
}
