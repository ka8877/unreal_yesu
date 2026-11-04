using System;

namespace PathOfDawn.Core
{
    /// <summary>A copy-on-migrate boundary: side-view coordinates never become field Z coordinates.</summary>
    public sealed class GospelPilgrimageLoad
    {
        public GospelJourney Journey { get; }
        public bool RequiresFork { get; }
        public bool CanRestorePose => !RequiresFork;

        internal GospelPilgrimageLoad(GospelJourney journey, bool fork)
        { Journey = journey; RequiresFork = fork; }
    }

    public static class GospelPilgrimageSave
    {
        public static GospelPilgrimageLoad Prepare(GospelSave original)
        {
            if (original == null) throw new ArgumentNullException(nameof(original));
            var next = GospelJourney.FromSave(original);
            bool fork = original.presentationSpace != GospelJourney.PilgrimageSpace || next.Chronicle == null;
            if (next.Chronicle == null) next.EnableChronicle();
            next.SetPresentationSpace(GospelJourney.PilgrimageSpace);
            // The actual world chooses a walkable spawn only after its chapter is built.
            // Keep the original DTO/slot intact and do not reuse old side-view Y or Z.
            if (fork) next.SetPlayerPose(0, 0, 0, 180);
            return new GospelPilgrimageLoad(next, fork);
        }
    }
}
